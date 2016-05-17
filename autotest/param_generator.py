# -*- coding:utf-8 -*-
from StringIO import StringIO



def get_example_from_prop_spec(self, prop_spec,param_name):
    """Return an example value from a property specification.

    Args:
        prop_spec: the specification of the property.

    Returns:
        An example value
    """
    if 'example' in prop_spec.keys() and self.use_example:  # From example
        return prop_spec['example']
    elif 'default' in prop_spec.keys():  # From default
        return prop_spec['default']
    elif 'enum' in prop_spec.keys():  # From enum return first one
        return prop_spec['enum'][0]
    elif '$ref' in prop_spec.keys():  # From definition
        return self._example_from_definition(prop_spec)
    elif 'type' not in prop_spec:  # Complex type
        return self._example_from_complex_def(prop_spec)
    elif prop_spec['type'] == 'array':  # Array
        return self._example_from_array_spec(prop_spec)
    elif prop_spec['type'] == 'file':  # File
        return (StringIO('my file contents'), 'hello world.txt')
    else:  # Basic types
        if 'format' in prop_spec.keys() and prop_spec['format'] == 'date-time':
            return self._get_example_from_basic_type('datetime')[0]
        else:
            return self._get_example_from_basic_type(prop_spec['type'],param_name)[0]



@staticmethod
def _get_example_from_basic_type(type,param_name):
    """Get example from the given type.

    Args:
        type: the type you want an example of.

    Returns:
        An array with two example values of the given type.
    """
    if type == 'integer':
        return [42, 24]
    elif type == 'number':
        return [5.5, 5.5]
    elif type == 'string':
        if param_name is 'media-id':
            return ['1243167573420321701_2027730041','1243167573420321701_2027730041']
        #return ['string', 'string2']
    elif type == 'datetime':
        return ['2015-08-28T09:02:57.481Z', '2015-08-28T09:02:57.481Z']
    elif type == 'boolean':
        return [False, True]

    #my change for instagram acess_token
    elif type == 'apiKey':
        return ['2027730041.7fbdb00.0c7f8721c1e74fccb52cb444e8beebf4','2027730041.7fbdb00.0c7f8721c1e74fccb52cb444e8beebf4']


def _example_from_definition(self, prop_spec):
    """Get an example from a property specification linked to a definition.

    Args:
        prop_spec: specification of the property you want an example of.

    Returns:
        An example.
    """
    # Get value from definition
    definition_name = self.get_definition_name_from_ref(prop_spec['$ref'])

    if self.build_one_definition_example(definition_name):
        example_dict = self.definitions_example[definition_name]
        if len(example_dict) == 1:
            return example_dict[example_dict.keys()[0]]
        else:
            example = {}
            for example_name, example_value in example_dict.items():
                example[example_name] = example_value
            return example

def _example_from_complex_def(self, prop_spec):
    """Get an example from a property specification.

    In case there is no "type" key in the root of the dictionary.

    Args:
        prop_spec: property specification you want an example of.

    Returns:
        An example.
    """
    if 'type' not in prop_spec['schema']:
        definition_name = self.get_definition_name_from_ref(prop_spec['schema']['$ref'])
        if self.build_one_definition_example(definition_name):
            return self.definitions_example[definition_name]
    elif prop_spec['schema']['type'] == 'array':  # Array with definition
        # Get value from definition
        if 'items' in prop_spec.keys():
            definition_name = self.get_definition_name_from_ref(prop_spec['items']['$ref'])
        else:
            definition_name = self.get_definition_name_from_ref(prop_spec['schema']['items']['$ref'])
        return [self.definitions_example[definition_name]]
    else:
        return self.get_example_from_prop_spec(prop_spec['schema'])

def _example_from_array_spec(self, prop_spec):
    """Get an example from a property specification of an array.

    Args:
        prop_spec: property specification you want an example of.

    Returns:
        An example array.
    """
    # Standard types in array
    if 'type' in prop_spec['items'].keys():
        if 'format' in prop_spec['items'].keys() and prop_spec['items']['format'] == 'date-time':
            return self._get_example_from_basic_type('datetime')
        else:
            return self._get_example_from_basic_type(prop_spec['items']['type'])

    # Array with definition
    elif '$ref' in prop_spec['items'].keys() or '$ref' in prop_spec['schema']['items'].keys():
        # Get value from definition
        definition_name = self.get_definition_name_from_ref(prop_spec['items']['$ref']) or \
                          self.get_definition_name_from_ref(prop_spec['schema']['items']['$ref'])
        if self.build_one_definition_example(definition_name):
            example_dict = self.definitions_example[definition_name]
            if len(example_dict) == 1:
                return example_dict[example_dict.keys()[0]]
            else:
                return_value = {}
                for example_name, example_value in example_dict.items():
                    return_value[example_name] = example_value
                return [return_value]

def instagram_example():
    return {
        'media-id':1243167573420321701,#图片
        #'media-id':1249879016396073767,#视频
        'user-id': 2027730041,#自己
        #'user-id': 1305584611,#王珞丹
        'tag-name':'cat',
        'q':'shoutaro_010',
        'shortcode':'BFDqZEgAKhm',
        'location-id':'213032512',
        'geo-id':'',
        'TEXT':'Hello!',
        #'count':1,
        'max_id':1243167573420321701,
        'min_id':1243167573420321701,
        'max_timestamp':None,
        'min_timestamp':None,
        #'max_like_id':1243167573420321701,
        'action':'follow',
        'LAT':None,
        'MIN_TIMESTAMP':None,
        'MAX_TIMESTAMP':None,
        'LNG':None,
        'DISTANCE':None
    }

def weibo_example():
    return{
        'access_token':'2.00DZF25D0VoLUHd3b86d0341gT8NxC',

    }

def uber_example():
    return {
        'latitude': 38.76623,
        'longitude':116.43213,
        'start_latitude':38.76623,
        'start_longitude':116.43213,
        'end_latitude':39.917023,
        'end_longitude':116.396813,
        'access_token':'CjCEg6plCW4SH1X3bVHjQKFpNtBeAD9TTcSVMg2k'
    }

def youku_example():
    return {
        'access_token': '24f0d08646c6b21bc5ad4ce8641e6e50',
        'client_id': '007ad73d2453bd70',
        'user_id': '87919223',
        'show_id': '2a7260de1faa11e097c0'
    }