import sm
import aslam_backend as aopt
import aslam_cv as cv
import kalibr_camera_calibration as kcc

import numpy as np
import collections
import itertools
import sys
import time
import heapq
try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except ImportError:
        Image = None

def _get_pl():
    try:
        import pylab as pl
        return pl
    except ImportError:
        return None

np.set_printoptions(suppress=True)


class _SimpleGraph(object):
    """Minimal graph (replaces igraph): vertices 0..n-1, weighted edges, connectivity, shortest path."""
    def __init__(self, n):
        self.n = n
        self.edges = []  # list of {u, v, weight, obs_ids} dicts
        self._adj = [[] for _ in range(n)]
        self._eid_map = {}  # (min(u,v), max(u,v)) -> edge_idx

    def _key(self, u, v):
        return (min(u, v), max(u, v))

    def add_edge(self, u, v, weight=0, obs_ids=None):
        k = self._key(u, v)
        if k in self._eid_map:
            return self._eid_map[k]
        idx = len(self.edges)
        self.edges.append({"u": u, "v": v, "weight": weight, "obs_ids": obs_ids or []})
        self._eid_map[k] = idx
        self._adj[u].append(v)
        self._adj[v].append(u)
        return idx

    def get_eid(self, u, v):
        k = self._key(u, v)
        if k not in self._eid_map:
            raise ValueError("Edge ({},{}) not found".format(u, v))
        return self._eid_map[k]

    def neighbors(self, v):
        return list(self._adj[v])

    def is_connected(self):
        if self.n <= 1:
            return True
        visited = [False] * self.n
        q = [0]
        visited[0] = True
        while q:
            v = q.pop()
            for w in self._adj[v]:
                if not visited[w]:
                    visited[w] = True
                    q.append(w)
        return all(visited)

    def dijkstra_path_edges(self, source, target, weights):
        """Returns list of edge indices on shortest path from source to target."""
        dist = [float('inf')] * self.n
        dist[source] = 0
        prev = [None] * self.n
        prev_edge = [None] * self.n
        pq = [(0, source)]
        while pq:
            d, v = heapq.heappop(pq)
            if d > dist[v]:
                continue
            if v == target:
                break
            for w in self._adj[v]:
                try:
                    ei = self.get_eid(v, w)
                except ValueError:
                    continue
                wt = weights[ei] if ei < len(weights) else 1.0
                nd = dist[v] + wt
                if nd < dist[w]:
                    dist[w] = nd
                    prev[w] = v
                    prev_edge[w] = ei
                    heapq.heappush(pq, (nd, w))
        path_edges = []
        v = target
        while prev[v] is not None:
            path_edges.append(prev_edge[v])
            v = prev[v]
        return path_edges

    def copy(self):
        g = _SimpleGraph(self.n)
        g.edges = [dict(e) for e in self.edges]
        g._eid_map = dict(self._eid_map)
        g._adj = [list(a) for a in self._adj]
        return g

    def delete_edges(self, eids):
        to_remove = set(eids)
        new_edges = []
        new_map = {}
        new_adj = [[] for _ in range(self.n)]
        for ei, e in enumerate(self.edges):
            if ei in to_remove:
                continue
            idx = len(new_edges)
            u, v = e["u"], e["v"]
            new_edges.append(e)
            new_map[self._key(u, v)] = idx
            new_adj[u].append(v)
            new_adj[v].append(u)
        self.edges = new_edges
        self._eid_map = new_map
        self._adj = new_adj


class MulticamCalibrationGraph(object):
    def __init__(self, obs_db):
        #observation database
        self.obs_db = obs_db
        self.numCams = self.obs_db.numCameras()
        
        #initialize the graph
        self.initializeGraphFromObsDb(self.obs_db)
    
    def initializeGraphFromObsDb(self, obs_db):
        t0 = time.time()
        G = _SimpleGraph(self.numCams)

        for timestamp in self.obs_db.getAllViewTimestamps():
            cam_ids_at_timestamp = set(obs_db.getCamIdsAtTimestamp(timestamp))
            possible_edges = itertools.combinations(cam_ids_at_timestamp, 2)

            for edge in possible_edges:
                cam_id_A, cam_id_B = edge[0], edge[1]
                corners_A = self.obs_db.getCornerIdsAtTime(timestamp, cam_id_A)
                obs_id_A = self.obs_db.getObsIdForCamAtTime(timestamp, cam_id_A)
                corners_B = self.obs_db.getCornerIdsAtTime(timestamp, cam_id_B)
                obs_id_B = self.obs_db.getObsIdForCamAtTime(timestamp, cam_id_B)
                common_corners = corners_A & corners_B

                if common_corners:
                    try:
                        edge_idx = G.get_eid(cam_id_A, cam_id_B)
                    except ValueError:
                        edge_idx = G.add_edge(cam_id_A, cam_id_B, weight=0, obs_ids=[])

                    G.edges[edge_idx]["weight"] += len(common_corners)
                    G.edges[edge_idx]["obs_ids"].append(
                        (obs_id_A, obs_id_B) if cam_id_A < cam_id_B else (obs_id_B, obs_id_A)
                    )

        self.G = G
        t1 = time.time()
        sm.logDebug("It took {0}s to build the graph.".format(t1 - t0))
    
#############################################################
## SYSTEM PROPERTIES
#############################################################    
    def isGraphConnected(self):
        if self.numCams == 1:
            return True
        return self.G.is_connected()

    def getCamOverlaps(self, cam_id):
        return self.G.neighbors(cam_id)
        
#############################################################
## INITIAL GUESS STUFF
#############################################################    
    
    #returns: 
    #        baselines:    list of baselines starting from cam0 to camN
    #                      direction: baseline_O => cam0 to cam1 (T_c1_c0)
    def getInitialGuesses(self, cameras):
        
        if not self.G:
            raise RuntimeError("Graph is uninitialized!")
        
        #################################################################
        ## STEP 0: check if all cameras in the chain are connected
        ##         through common target point observations
        ##         (=all vertices connected?)
        #################################################################
        if not self.isGraphConnected():
            sm.logError("The cameras are not connected through mutual target observations! "
                        "Please provide another dataset...")
            self.plotGraph()
            sys.exit(0)

        weights = [1.0 / e["weight"] for e in self.G.edges]
        edges_on_path = []
        for t in range(1, self.numCams):
            edges_on_path.append(self.G.dijkstra_path_edges(0, t, weights))
        self.optimal_baseline_edges = set(ei for sublist in edges_on_path for ei in sublist)
        
        
        #################################################################
        ## STEP 2: solve stereo calibration problem for the baselines
        ##         (baselines are always from lower_id to higher_id cams!)
        #################################################################
        
        for baseline_edge_id in self.optimal_baseline_edges:
            e = self.G.edges[baseline_edge_id]
            camL_nr, camH_nr = min(e["u"], e["v"]), max(e["u"], e["v"])
            print("\t initializing camera pair ({0},{1})...  ".format(camL_nr, camH_nr))
            obs_list = self.obs_db.getAllObsTwoCams(camL_nr, camH_nr)
            success, baseline_HL = kcc.stereoCalibrate(cameras[camL_nr], cameras[camH_nr],
                                                       obs_list, distortionActive=False)
            if success:
                sm.logDebug("baseline_{0}_{1}={2}".format(camL_nr, camH_nr, baseline_HL.T()))
            else:
                sm.logError("initialization of camera pair ({0},{1}) failed  ".format(camL_nr, camH_nr))
                sm.logError("estimated baseline_{0}_{1}={2}".format(camL_nr, camH_nr, baseline_HL.T()))
            self.G.edges[self.G.get_eid(camL_nr, camH_nr)]["baseline_HL"] = baseline_HL
        
        #################################################################
        ## STEP 3: transform from the "optimal" baseline chain to camera chain ordering
        ##         (=> baseline_0 = T_c1_c0 | 
        #################################################################
        
        G_optimal_baselines = self.G.copy()
        eid_not_optimal = set(range(len(G_optimal_baselines.edges))) - self.optimal_baseline_edges
        G_optimal_baselines.delete_edges(list(eid_not_optimal))

        weights = [1.0 / e["weight"] for e in G_optimal_baselines.edges]
        baselines = []
        for baseline_id in range(0, self.numCams - 1):
            path_edges = G_optimal_baselines.dijkstra_path_edges(baseline_id, baseline_id + 1, weights)
            baseline_HL = sm.Transformation()
            for ei in path_edges:
                e = G_optimal_baselines.edges[ei]
                u, v = e["u"], e["v"]
                T_edge = e["baseline_HL"]
                T_edge = T_edge if u < v else T_edge.inverse()
                baseline_HL = T_edge * baseline_HL
            baselines.append(baseline_HL)
 
        #################################################################
        ## STEP 4: refine guess in full batch
        #################################################################
        success, baselines = kcc.solveFullBatch(cameras, baselines, self)
        
        if not success:
            sm.logWarn("Full batch refinement failed!")
    
        return baselines
    
    def getTargetPoseGuess(self, timestamp, cameras, baselines_HL=[]):
        #go through all camera that see this target at the given time
        #and take the one with the most target points        
        camids = list()
        numcorners = list()
        for cam_id in self.obs_db.getCamIdsAtTimestamp(timestamp):
            camids.append(cam_id)
            numcorners.append( len(self.obs_db.getCornerIdsAtTime(timestamp, cam_id)) )

        #get the pnp solution of the cam that sees most target corners
        max_idx = numcorners.index(max(numcorners))
        cam_id_max = camids[max_idx]        
        
        #solve the pnp problem
        camera_geomtry = cameras[cam_id_max].geometry
        success, T_t_cN = camera_geomtry.estimateTransformation(self.obs_db.getObservationAtTime(timestamp, cam_id_max))
               
        if not success:
            sm.logWarn("getTargetPoseGuess: solvePnP failed with solution: {0}".format(T_t_cN))
        
        #transform it back to cam0 (T_t_cN --> T_t_c0)
        T_cN_c0 = sm.Transformation()
        for baseline_HL in baselines_HL[0:cam_id_max]:
            T_cN_c0 = baseline_HL * T_cN_c0
        
        T_t_c0 = T_t_cN * T_cN_c0
        
        return T_t_c0
    
    def getAllMutualObsBetweenTwoCams(self, camA_nr, camB_nr):
        try:
            edge_idx = self.G.get_eid(camA_nr, camB_nr)
        except ValueError:
            sm.logError("getAllMutualObsBetweenTwoCams: no mutual observations between the two cams!")
            return [], []
        observations = self.G.edges[edge_idx]["obs_ids"]
        
        #extract the ids
        obs_idx_L = [obs_ids[0] for obs_ids in observations]
        obs_idx_H = [obs_ids[1] for obs_ids in observations]
        
        #the first value of the tuple always stores the obsvervations for camera
        #with the lower id
        obs_idx_A = obs_idx_L if camA_nr<camB_nr else obs_idx_H
        obs_idx_B = obs_idx_H if camA_nr<camB_nr else obs_idx_L
        
        #get the obs from the storage using idx
        obs_A = [self.obs_db.observations[camA_nr][idx] for idx in obs_idx_A]
        obs_B = [self.obs_db.observations[camB_nr][idx] for idx in obs_idx_B]

        return obs_A, obs_B
         
    def plotGraph(self, noShow=False):
        # No igraph: skip graph visualization (headless)
        return None

    def plotGraphPylab(self, fno=0, noShow=True, clearFigure=True, title=""):
        pl = _get_pl()
        if pl is None or Image is None:
            return
        target = self.plotGraph(noShow=True)
        if target is None:
            return
        f = pl.figure(fno)
        if clearFigure:
            f.clf()
        f.suptitle(title)
        img = Image.open(target)
        pl.imshow(np.array(img))
        pl.axis('off')
        if not noShow:
            pl.show()
