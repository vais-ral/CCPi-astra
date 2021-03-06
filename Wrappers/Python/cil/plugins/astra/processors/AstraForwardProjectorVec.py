from cil.framework import DataProcessor, AcquisitionData, DataOrder
from cil.plugins.astra.utilities import convert_geometry_to_astra_vec
import astra
from astra import astra_dict, algorithm, data3d
import numpy as np

class AstraForwardProjectorVec(DataProcessor):
    '''AstraForwardProjectorVec
    
    Forward project ImageData to AcquisitionData using ASTRA projector.
    
    Input: ImageData
    Output: AcquisitionData
    '''

    def __init__(self,
                 volume_geometry=None,
                 sinogram_geometry=None,
                 proj_geom=None,
                 vol_geom=None):
        kwargs = {
                  'volume_geometry'  : volume_geometry,
                  'sinogram_geometry'  : sinogram_geometry,
                  'proj_geom'  : proj_geom,
                  'vol_geom'  : vol_geom,
                  }
        
        super(AstraForwardProjectorVec, self).__init__(**kwargs)
        
        self.set_ImageGeometry(volume_geometry)
        self.set_AcquisitionGeometry(sinogram_geometry)
        
        self.vol_geom, self.proj_geom = convert_geometry_to_astra_vec(self.volume_geometry, self.sinogram_geometry)
        
    def check_input(self, dataset):

        if self.volume_geometry.shape != dataset.geometry.shape:
            raise ValueError("Dataset not compatible with geometry used to create the projector")  
    
        return True
    
    def set_ImageGeometry(self, volume_geometry):

        DataOrder.check_order_for_engine('astra', volume_geometry)

        if len(volume_geometry.dimension_labels) > 3:
            raise ValueError("Supports 2D and 3D data only, got {0}".format(volume_geometry.number_of_dimensions))  

        self.volume_geometry = volume_geometry.copy()

    def set_AcquisitionGeometry(self, sinogram_geometry):

        DataOrder.check_order_for_engine('astra', sinogram_geometry)

        if len(sinogram_geometry.dimension_labels) > 3:
            raise ValueError("Supports 2D and 3D data only, got {0}".format(volume_geometry.number_of_dimensions))  

        self.sinogram_geometry = sinogram_geometry.copy()


    def process(self, out=None):

        IM = self.get_input()

        pad = False
        if len(IM.shape) == 2:
            #for 2D cases
            pad = True
            data_temp = np.expand_dims(IM.as_array(),axis=0)
        else:
            data_temp = IM.as_array()

        if out is None:

            sinogram_id, arr_out = astra.create_sino3d_gpu(data_temp, 
                                                           self.proj_geom,
                                                           self.vol_geom)
        else:
            if pad:
                arr_out = np.expand_dims(out.as_array(), axis=0)
            else:
                arr_out = out.as_array()
                
            sinogram_id = astra.data3d.link('-sino', self.proj_geom, arr_out)
            self.create_backprojection3d_gpu(data_temp, self.proj_geom, self.vol_geom, False, sinogram_id)

        #clear the memory on GPU
        astra.data3d.delete(sinogram_id)
        
        if pad is True:
            arr_out = np.squeeze(arr_out, axis=0)

        if out is None:
            out = AcquisitionData(arr_out, deep_copy=False, geometry=self.sinogram_geometry.copy(), suppress_warning=True)
            return out
        else:
            out.fill(arr_out)

    def create_sino3d_gpu(data, proj_geom, vol_geom, returnData=True, gpuIndex=None, sino_id=None):
        """Create a forward projection of an image (3D).
    :param data: Image data or ID.
    :type data: :class:`numpy.ndarray` or :class:`int`
    :param proj_geom: Projection geometry.
    :type proj_geom: :class:`dict`
    :param vol_geom: Volume geometry.
    :type vol_geom: :class:`dict`
    :param returnData: If False, only return the ID of the forward projection.
    :type returnData: :class:`bool`
    :param gpuIndex: Optional GPU index.
    :type gpuIndex: :class:`int`
    :returns: :class:`int` or (:class:`int`, :class:`numpy.ndarray`) -- If ``returnData=False``, returns the ID of the forward projection. Otherwise, returns a tuple containing the ID of the forward projection and the forward projection itself, in that order.
    """

        if isinstance(data, np.ndarray):
            volume_id = data3d.create('-vol', vol_geom, data)
        else:
            volume_id = data
        if sino_id is None:
            sino_id = data3d.create('-sino', proj_geom, 0)

        algString = 'FP3D_CUDA'
        cfg = astra_dict(algString)
        if not gpuIndex==None:
            cfg['option']={'GPUindex':gpuIndex}
        cfg['ProjectionDataId'] = sino_id
        cfg['VolumeDataId'] = volume_id
        alg_id = algorithm.create(cfg)
        algorithm.run(alg_id)
        algorithm.delete(alg_id)

        if isinstance(data, np.ndarray):
            data3d.delete(volume_id)
        if sino_id is None:
            if returnData:
                return sino_id, data3d.get(sino_id)
            else:
                return sino_id
        else:
            if returnData:
                return sino_id, data3d.get_shared(sino_id)
            else:
                return sino_id

