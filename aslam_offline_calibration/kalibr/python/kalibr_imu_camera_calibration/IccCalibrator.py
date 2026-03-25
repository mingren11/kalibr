import aslam_backend as aopt
import aslam_splines as asp
from . import IccUtil as util
import incremental_calibration as inc
import kalibr_common as kc
import sm

import gc
import numpy as np
import multiprocessing
import sys

# make numpy print prettier
np.set_printoptions(suppress=True)

CALIBRATION_GROUP_ID = 0
HELPER_GROUP_ID = 1

def addSplineDesignVariables(problem, dvc, setActive=True, group_id=HELPER_GROUP_ID):
    for i in range(0,dvc.numDesignVariables()):
        dv = dvc.designVariable(i)
        dv.setActive(setActive)
        problem.addDesignVariable(dv, group_id)

class IccCalibrator(object):
    def __init__(self):
        self.ImuList = []

    def initDesignVariables(self, problem, poseSpline, noTimeCalibration, noChainExtrinsics=True, \
                            estimateGravityLength=False, initialGravityEstimate=np.array([0.0,9.81,0.0])):        
        # Initialize the system pose spline (always attached to imu0) 
        self.poseDv = asp.BSplinePoseDesignVariable( poseSpline )
        addSplineDesignVariables(problem, self.poseDv)

        # Add the calibration target orientation design variable. (expressed as gravity vector in target frame)
        if estimateGravityLength:
            self.gravityDv = aopt.EuclideanPointDv( initialGravityEstimate )
        else:
            self.gravityDv = aopt.EuclideanDirection( initialGravityEstimate )
        self.gravityExpression = self.gravityDv.toExpression()  
        self.gravityDv.setActive( True )
        problem.addDesignVariable(self.gravityDv, HELPER_GROUP_ID)
        
        #Add all DVs for all IMUs
        for imu in self.ImuList:
            imu.addDesignVariables( problem )
        
        #Add all DVs for the camera chain    
        self.CameraChain.addDesignVariables( problem, noTimeCalibration, noChainExtrinsics )

    def addPoseMotionTerms(self, problem, tv, rv):
        wt = 1.0/tv;
        wr = 1.0/rv
        W = np.diag([wt,wt,wt,wr,wr,wr])
        asp.addMotionErrorTerms(problem, self.poseDv, W, errorOrder)
        
    #add camera to sensor list (create list if necessary)
    def registerCamChain(self, sensor):
        self.CameraChain = sensor

    def registerImu(self, sensor):
        self.ImuList.append( sensor )
            
    def buildProblem( self, 
                      splineOrder=6, 
                      poseKnotsPerSecond=70, 
                      biasKnotsPerSecond=70, 
                      doPoseMotionError=False, 
                      mrTranslationVariance=1e6,
                      mrRotationVariance=1e5,
                      doBiasMotionError=True,
                      blakeZisserCam=-1,
                      huberAccel=-1,
                      huberGyro=-1,
                      noTimeCalibration=False,
                      noChainExtrinsics=True,
                      maxIterations=20,
                      gyroNoiseScale=1.0,
                      accelNoiseScale=1.0,
                      timeOffsetPadding=0.02,
                      verbose=False  ):

        print("\tSpline order: %d" % (splineOrder))
        print("\tPose knots per second: %d" % (poseKnotsPerSecond))
        print("\tDo pose motion regularization: %s" % (doPoseMotionError))
        print("\t\txddot translation variance: %f" % (mrTranslationVariance))
        print("\t\txddot rotation variance: %f" % (mrRotationVariance))
        print("\tBias knots per second: %d" % (biasKnotsPerSecond))
        print("\tDo bias motion regularization: %s" % (doBiasMotionError))
        print("\tBlake-Zisserman on reprojection errors %s" % blakeZisserCam)
        print("\tAcceleration Huber width (sigma): %f" % (huberAccel))
        print("\tGyroscope Huber width (sigma): %f" % (huberGyro))
        print("\tDo time calibration: %s" % (not noTimeCalibration))
        print("\tMax iterations: %d" % (maxIterations))
        print("\tTime offset padding: %f" % (timeOffsetPadding))


        ############################################
        ## initialize camera chain
        ############################################
        #estimate the timeshift for all cameras to the main imu
        self.noTimeCalibration = noTimeCalibration
        if not noTimeCalibration:
            for cam in self.CameraChain.camList:
                cam.findTimeshiftCameraImuPrior(self.ImuList[0], verbose)
        
        #obtain orientation prior between main imu and camera chain (if no external input provided)
        #and initial estimate for the direction of gravity
        self.CameraChain.findOrientationPriorCameraChainToImu(self.ImuList[0])
        estimatedGravity = self.CameraChain.getEstimatedGravity()

        ############################################
        ## init optimization problem
        ############################################
        #initialize a pose spline using the camera poses in the camera chain
        poseSpline = self.CameraChain.initializePoseSplineFromCameraChain(splineOrder, poseKnotsPerSecond, timeOffsetPadding)
        
        # Initialize bias splines for all IMUs
        for imu in self.ImuList:
            imu.initBiasSplines(poseSpline, splineOrder, biasKnotsPerSecond)
        
        # Now I can build the problem
        problem = inc.CalibrationOptimizationProblem()

        # Initialize all design variables.
        self.initDesignVariables(problem, poseSpline, noTimeCalibration, noChainExtrinsics, initialGravityEstimate = estimatedGravity)
        
        ############################################
        ## add error terms
        ############################################
        #Add calibration target reprojection error terms for all camera in chain
        self.CameraChain.addCameraChainErrorTerms(problem, self.poseDv, blakeZissermanDf=blakeZisserCam, timeOffsetPadding=timeOffsetPadding)
        
        # Initialize IMU error terms.
        for imu in self.ImuList:
            imu.addAccelerometerErrorTerms(problem, self.poseDv, self.gravityExpression, mSigma=huberAccel, accelNoiseScale=accelNoiseScale)
            imu.addGyroscopeErrorTerms(problem, self.poseDv, mSigma=huberGyro, gyroNoiseScale=gyroNoiseScale, g_w=self.gravityExpression)

            # Add the bias motion terms.
            if doBiasMotionError:
                imu.addBiasMotionTerms(problem)
            
        # Add the pose motion terms.
        if doPoseMotionError:
            self.addPoseMotionTerms(problem, mrTranslationVariance, mrRotationVariance)
        
        # Add a gravity prior
        self.problem = problem


    def optimize(self, options=None, maxIterations=30, recoverCov=False):

        if options is None:
            options = aopt.Optimizer2Options()
            options.verbose = True
            options.doLevenbergMarquardt = True
            options.levenbergMarquardtLambdaInit = 10.0
            options.nThreads = max(1,multiprocessing.cpu_count()-1)
            options.convergenceDeltaX = 1e-5
            options.convergenceDeltaJ = 1e-2
            options.maxIterations = maxIterations
            options.trustRegionPolicy = aopt.LevenbergMarquardtTrustRegionPolicy(options.levenbergMarquardtLambdaInit)
            options.linearSolver = aopt.BlockCholeskyLinearSystemSolver() #does not have multi-threading support

        #run the optimization
        self.optimizer = aopt.Optimizer2(options)
        self.optimizer.setProblem(self.problem)

        optimizationFailed=False
        try:
            retval = self.optimizer.optimize()
            if retval.linearSolverFailure:
                optimizationFailed = True
        except Exception as e:
            sm.logError(str(e))
            optimizationFailed = True

        if optimizationFailed:
            sm.logError("Optimization failed!")
            raise RuntimeError("Optimization failed!")
        
        #free some memory
        del self.optimizer
        gc.collect()
        if recoverCov:
            self.recoverCovariance()
        

    def recoverCovariance(self):
        #Covariance ordering (=dv ordering)
        #ORDERING:   N=num cams
        #            1. transformation imu-cam0 --> 6
        #            2. camera time2imu --> 1*numCams (only if enabled)
        
        print("Recovering covariance...")
        estimator = inc.IncrementalEstimator(CALIBRATION_GROUP_ID)
        rval = estimator.addBatch(self.problem, True)    
        est_stds = np.sqrt(estimator.getSigma2Theta().diagonal())
        
        #split and store the variance
        self.std_trafo_ic = np.array(est_stds[0:6])
        self.std_times = np.array(est_stds[6:])
    
    def saveImuSetParametersYaml(self, resultFile):
        imuSetConfig = kc.ImuSetParameters(resultFile, True)
        for imu in self.ImuList:
            imuConfig = imu.getImuConfig()
            imuSetConfig.addImuParameters(imu_parameters=imuConfig)
        imuSetConfig.writeYaml(resultFile)

    def saveCamChainParametersYaml(self, resultFile):    
        chain = self.CameraChain.chainConfig
        nCams = len(self.CameraChain.camList)
    
        # Calibration results
        for camNr in range(0,nCams):
            #cam-cam baselines           
            if camNr > 0:
                T_cB_cA, baseline = self.CameraChain.getResultBaseline(camNr-1, camNr)
                chain.setExtrinsicsLastCamToHere(camNr, T_cB_cA)

            #imu-cam trafos
            T_ci = self.CameraChain.getResultTrafoImuToCam(camNr)
            chain.setExtrinsicsImuToCam(camNr, T_ci)

            if not self.noTimeCalibration:
                #imu to cam timeshift
                timeshift = float(self.CameraChain.getResultTimeShift(camNr))
                chain.setTimeshiftCamImu(camNr, timeshift)
             
        try:
            chain.writeYaml(resultFile)
        except:
            raise RuntimeError("ERROR: Could not write parameters to file: {0}\n".format(resultFile))

    def saveLooperJson(self, resultFile):
        """Save calibration results as looper.json.

        Format:
            base_name: "IMU"
            camera_calibrations[i].extrinsics.pose_base_in_sensor
                = pose of IMU (base) in camera_i frame  =  T_cam_imu
            camera_calibrations[i].intrinsics
                = calibrated camera intrinsics (same as input, IMU-cam
                  calibration does not optimise intrinsics)
        """
        import json as _json

        def _R_to_quat(R):
            """Rotation matrix (3x3 numpy) -> (w, x, y, z) unit quaternion."""
            trace = R[0, 0] + R[1, 1] + R[2, 2]
            if trace > 0:
                s = 0.5 / np.sqrt(trace + 1.0)
                w = 0.25 / s
                x = (R[2, 1] - R[1, 2]) * s
                y = (R[0, 2] - R[2, 0]) * s
                z = (R[1, 0] - R[0, 1]) * s
            elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
                s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
                w = (R[2, 1] - R[1, 2]) / s
                x = 0.25 * s
                y = (R[0, 1] + R[1, 0]) / s
                z = (R[0, 2] + R[2, 0]) / s
            elif R[1, 1] > R[2, 2]:
                s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
                w = (R[0, 2] - R[2, 0]) / s
                x = (R[0, 1] + R[1, 0]) / s
                y = 0.25 * s
                z = (R[1, 2] + R[2, 1]) / s
            else:
                s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
                w = (R[1, 0] - R[0, 1]) / s
                x = (R[0, 2] + R[2, 0]) / s
                y = (R[1, 2] + R[2, 1]) / s
                z = 0.25 * s
            return float(w), float(x), float(y), float(z)

        chain = self.CameraChain.chainConfig
        nCams = len(self.CameraChain.camList)
        camera_calibrations = []

        for camNr in range(nCams):
            # T_cam_imu: pose of IMU expressed in camera frame
            T_cam_imu = self.CameraChain.getResultTrafoImuToCam(camNr)
            T_mat = T_cam_imu.T()
            R = T_mat[:3, :3]
            t = T_mat[:3, 3]
            w, x, y, z = _R_to_quat(R)

            # Intrinsics from chain (not re-optimised during IMU-cam calib)
            camConfig = chain.getCameraParameters(camNr)
            camera_model, intrinsics = camConfig.getIntrinsics()
            dist_model, dist_coeff   = camConfig.getDistortion()
            resolution               = camConfig.getResolution()   # [width, height]

            fx, fy = float(intrinsics[0]), float(intrinsics[1])
            cx, cy = float(intrinsics[2]), float(intrinsics[3])
            width, height = int(resolution[0]), int(resolution[1])

            # Map kalibr model names back to the looper convention
            if camera_model == 'pinhole' and dist_model == 'equidistant':
                model_out = 'FISHEYE'
            else:
                model_out = camera_model.upper()

            # Recover original camera_name if available, else derive from topic
            cam_data = chain.data.get('cam{0}'.format(camNr), {})
            cam_name = cam_data.get('camera_name', None)
            if cam_name is None:
                topic    = camConfig.getRosTopic()
                cam_name = topic.strip('/').split('/')[0].upper().replace('-', '_')

            camera_calibrations.append({
                "camera_name": cam_name,
                "extrinsics": {
                    "pose_base_in_sensor": {
                        "rotation":    {"w": w, "x": x, "y": y, "z": z},
                        "translation": {"x": float(t[0]), "y": float(t[1]), "z": float(t[2])}
                    }
                },
                "intrinsics": {
                    "camera_model":    model_out,
                    "cx":              cx,
                    "cy":              cy,
                    "distortion_coef": [float(c) for c in dist_coeff],
                    "fx":              fx,
                    "fy":              fy,
                    "height":          height,
                    "width":           width
                }
            })

        output = {"base_name": "IMU", "camera_calibrations": camera_calibrations}
        try:
            with open(resultFile, 'w') as f:
                _json.dump(output, f, indent=2)
        except Exception as e:
            raise RuntimeError("ERROR: Could not write looper.json to {0}: {1}".format(resultFile, e))
