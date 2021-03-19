from cil.framework import DataProcessor, AcquisitionData
from cil.plugins.astra.utilities import convert_geometry_to_astra_vec
import astra
import numpy

class AstraForwardProjectorVec(DataProcessor):
    '''AstraForwardProjectorVec
    
    Forward project ImageData to AcquisitionData using ASTRA proj_id.
    
    Input: ImageData
    Parameter: proj_id
    Output: AcquisitionData
    '''
    ASTRA_LABELS_VOL_3D = ['vertical','horizontal_y','horizontal_x']
    ASTRA_LABELS_PROJ_3D = ['vertical','angle','horizontal']
    ASTRA_LABELS_VOL_2D = ['horizontal_y','horizontal_x']
    ASTRA_LABELS_PROJ_2D = ['angle','horizontal']

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
        dim = len(dataset.dimension_labels)

        if dim == 3:
            order = [dataset.dimension_labels[0],dataset.dimension_labels[1],dataset.dimension_labels[2]]
            if order != AstraForwardProjectorVec.ASTRA_LABELS_VOL_3D:
                raise ValueError("Acquistion geometry expects dimension label order {0} for ASTRA compatibility got {1}".format(AstraForwardProjectorVec.ASTRA_LABELS_VOL_3D, order))  
        elif dim == 2:
            order = [dataset.dimension_labels[0],dataset.dimension_labels[1]]
            if order != AstraForwardProjectorVec.ASTRA_LABELS_VOL_2D:
                raise ValueError("Acquistion geometry expects dimension label order {0} for ASTRA compatibility got {1}".format(AstraForwardProjectorVec.ASTRA_LABELS_VOL_2D, order))  
        else:
            raise ValueError("Supports 2D and 3D data only, got {0}".format(dataset.number_of_dimensions))  

        return True
    
    def set_ImageGeometry(self, volume_geometry):
        
        dim = len(volume_geometry.dimension_labels)
        if dim == 3:
            order = [volume_geometry.dimension_labels[0],volume_geometry.dimension_labels[1],volume_geometry.dimension_labels[2]]
            if order != AstraForwardProjectorVec.ASTRA_LABELS_VOL_3D:
                raise ValueError("Acquistion geometry expects dimension label order {0} for ASTRA compatibility got {1}".format(AstraForwardProjectorVec.ASTRA_LABELS_VOL_3D, order))  
        elif dim == 2:
            order = [volume_geometry.dimension_labels[0],volume_geometry.dimension_labels[1]]
            if order != AstraForwardProjectorVec.ASTRA_LABELS_VOL_2D:
                raise ValueError("Acquistion geometry expects dimension label order {0} for ASTRA compatibility got {1}".format(AstraForwardProjectorVec.ASTRA_LABELS_VOL_2D, order))  
        else:
            raise ValueError("Supports 2D and 3D data only, got {0}".format(volume_geometry.number_of_dimensions))  

        self.volume_geometry = volume_geometry.copy()

    def set_AcquisitionGeometry(self, sinogram_geometry):

        dim = len(sinogram_geometry.dimension_labels)

        if dim == 3:
            order = [sinogram_geometry.dimension_labels[0],sinogram_geometry.dimension_labels[1],sinogram_geometry.dimension_labels[2]]
            if order != AstraForwardProjectorVec.ASTRA_LABELS_PROJ_3D:
                raise ValueError("Acquistion geometry expects dimension label order {0} for ASTRA compatibility got {1}".format(AstraForwardProjectorVec.ASTRA_LABELS_PROJ_3D, order))  
        elif dim == 2:
            order = [sinogram_geometry.dimension_labels[0],sinogram_geometry.dimension_labels[1]]
            if order != AstraForwardProjectorVec.ASTRA_LABELS_PROJ_2D:
                raise ValueError("Acquistion geometry expects dimension label order {0} for ASTRA compatibility got {1}".format(AstraForwardProjectorVec.ASTRA_LABELS_PROJ_2D, order))  
        else:
            raise ValueError("Supports 2D and 3D data only, got {0}".format(sinogram_geometry.number_of_dimensions))  

        self.sinogram_geometry = sinogram_geometry.copy()


    def process(self, out=None):

        IM = self.get_input()

        pad = False
        if len(IM.shape) == 2:
            #for 2D cases
            pad = True
            data_temp = numpy.expand_dims(IM.as_array(),axis=0)
        else:
            data_temp = IM.as_array()

        sinogram_id, arr_out = astra.create_sino3d_gpu(data_temp, 
                                                           self.proj_geom,
                                                           self.vol_geom)

        astra.data3d.delete(sinogram_id)
        
        if pad is True:
            arr_out = numpy.squeeze(arr_out, axis=0)

        if out is None:
            out = AcquisitionData(arr_out, deep_copy=False, geometry=self.sinogram_geometry.copy(), suppress_warning=True)
            return out
        else:
            out.fill(arr_out)
