
from bmesh.types import BMElemSeq, BMEdgeSeq, BMFaceSeq, BMVertSeq
from bmesh.types import BMVert, BMEdge, BMFace, BMesh, BMLoop
from bpy import context
from bpy.types import Object, Operator, Panel, ID
from bmesh import from_edit_mesh, update_edit_mesh
from typing import List, Tuple, Dict, Any, TypeVar, Generator, Callable, Set, DefaultDict, Reversible
from queue import PriorityQueue
from state_edge.stateEdges import StateEdge
"""https://stackoverflow.com/questions/5834014/lf-will-be-replaced-by-crlf-in-git-what-is-that-and-is-it-important """
def overrides(interface_class:object)->Callable:
    def overrider(method:Callable)->Callable:
        classMethod:str = '_FacesAnglePathSelectionManager' + method.__name__
        print(classMethod)
        assert(classMethod in dir(interface_class)), "method name was not found in the interface class"
        return method
    return overrider

class LengthEdgePathSelectionManager(Operator):
    bl_idname: str = 'lengthscore.selectionmanager';
    bl_label: str = 'show searching path based on edge length';
    bl_options: Set[str] = {'REGISTER', 'UNDO'};
    def __init__(self) -> None:
        self.__obj:Object = context.object;
        self.__bm:BMesh;
        self.__selectedEdges:List[BMEdgeSeq] = list();
        self.__priorityQueue:PriorityQueue=PriorityQueue()
        self.__angles:List[float] = list()
    def __getEdges(self) -> List[BMEdgeSeq]:
        return self.__selectedEdges
    def __addStatesToRandList(self, state:StateEdge) -> None:
        self.__priorityQueue.put(state);
    def __deleteAllEdges(self) -> None:
        while not(self.__priorityQueue.empty()):
            try:
                self.__priorityQueue.get(False)
            except Exception:
                continue
            self.__priorityQueue.task_done()
    def calculateFacesAngle(self) -> None:
        pass
    def __setSelectedEdges(self)->None:
        length:int;
        if(self.__obj.mode == 'EDIT'):
            self.__bm = from_edit_mesh(self.__obj.data)
            length=len(self.__bm.edges)
            for i in range(length):
                if(self.__bm.edges[i].select):
                    #print('selected edges: {}'.format(self.__bm.edges[i]))
                    self.__selectedEdges.append(self.__bm.edges[i])
        else:
            print("Object is not in edit mode.")
    def __randListe(self, state:StateEdge=None)->None:
        assert (state is not None),'state ist NoneType';
        assert(len(state.children)>0),'Children´s List is Empty';
        editedChildren:List[BMEdge]= None;
        children:List[StateEdge] = state.children[:]
        parentChildren:List[StateEdge] = state.parent.children[:] if(state.parent is not None) else None;
        if(parentChildren is not None):
            editedChildren = children + parentChildren;
            for i in range(len(editedChildren)):
                self.__addStatesToRandList(editedChildren[i])
        else:
            for j in range(len(children)):
                self.__addStatesToRandList(children[j])
    def __excludeDuplicates(self) -> List[int]:
        i:int;
        currIndex:int
        indices:List[BMEdge] = list();
        if (len(self.__selectedEdges)==1):
            return [self.__selectedEdges[0].index]
        elif(len(self.__selectedEdges)<1):
            print('the list ist empty')
        for i in range(len(self.__selectedEdges)):
            indices.append(self.__selectedEdges[i].index) # saves the indices
        return list(set(indices)) # removes the duplicates
    @staticmethod
    def __checkNodeInStatus(action:StateEdge, currState:StateEdge)->bool:
        assert ((currState is not None) and (action is not None)), 'it can not create children because the parent is NoneType';
        vertices: List[BMVert] = [vert for vert in action.action.verts]
        if(currState.node in vertices):
            return True
        else:
            return False  # ------- > ändere das was hier zurückgeliefert wird
    @staticmethod
    def __extractStatesParents(stateValue: StateEdge) -> List[BMEdge]:
        parents: List[BMEdge] = list()
        action: StateEdge = stateValue.parent;
        if (action is not None): parents.append(action.action);
        i: int = 0
        while(True):
            if (action.parent is None):
                break
            try:
                action = action.parent
                parents.append(action.action)
            except Exception as e:
                print('[Exception] :', e)
            i += 1
        return parents
    def __constructEdgePath(self) -> List[BMEdge]:
        # start: int = 0;
        visited: List[int] = self.__excludeDuplicates() # list of edge indices [False] * len(self.__selectedEdges)
        nextEdge:BMEdge;
        parentNode:bool;
        actions:List[BMEdge]=list();
        # -------- clear dict EXTENDED NODES
        self.__deleteAllEdges()
        # ------------ declare and define StateEdges, first call has none SCORE
        state:StateEdge = StateEdge(parent=None,action=self.__selectedEdges[0]);
        # ------ create children-edges
        state.createChildrenEdges(scoreAngle=False);
        # ------ save the RAND LIST as a priority queue
        self.__randListe(state)
        while(True): # endlose Schleife
            # ------ look for the next edge and save in SELECTED EDGES
            nextEdge = self.__priorityQueue.get()
            assert (nextEdge is not None), 'there is none new selected edge'
            if(nextEdge.action == state.goal):
                visited.append(nextEdge.action.index);
                state = StateEdge(parent=state, action=nextEdge.action);
                self.__selectedEdges.append(state.action);
                print(' the goal EDGE {} was selected and added into SELECTED EDGES!'.format(nextEdge.action));
                self.__addStatesToRandList(state)
                actions.append(self.__extractStatesParents(state))
                break;
            elif(nextEdge.action.index not in visited):
                # start+=1;
                visited.append(nextEdge.action.index);
                self.__selectedEdges.append(nextEdge.action)
            elif(nextEdge.action.index in visited):
                continue
            # -------- check if parent node in current edge
            parentNode = self.__checkNodeInStatus(nextEdge,state)
            # ------- save the last node, action and children into the class itself
            if(parentNode is True):
                state = StateEdge(state, nextEdge.action)
                # ------ calculate the score for the current edge
                state.calculateTheScore(angleScore=True)
            else:
                # ------ the last state will be saved into the priority queue
                self.__addStatesToRandList(state);
                state = nextEdge
            # ------ create children-edges
            state.createChildrenEdges(scoreAngle=True);
            # -------- save the status in EXTENDED NODES
            self.__randListe(state);
            # start+=1;
        return actions
    def __activateEdgesEDITMODE(self,EDGES:List[List[BMEdge]]) -> None:
        i:int;
        currEdge:BMEdge;
        for i in range(len(EDGES[0])):
            currEdge = EDGES[0][i]
            currEdge.select=True;
            self.__bm.select_history.clear();
            self.__bm.select_history.add(currEdge);
        update_edit_mesh(self.__obj.data)
    def execute(self, context) -> Set[str]:
        actions:List[List[BMEdge]];
        self.__selectedEdges.clear()
        try:
            self.__setSelectedEdges()
            assert(len(self.__selectedEdges)>0),'None Edge was selected, please select a edge in EDIT MODE'
            actions = self.__constructEdgePath()
            self.__activateEdgesEDITMODE(actions)
            context.scene.long_string = '[Output Info]:{}'.format(len(actions[0]))
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, e.args)
            return {'CANCELLED'}