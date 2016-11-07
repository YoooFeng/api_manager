# -*- coding: utf-8 -*-

import json
import logging
import logging.handlers
import requests
import six
import time
import param_generator
import tablib

try:
    from urllib import urlencode
except ImportError:  # Python 3
    from urllib.parse import urlencode



from swagger_parser import SwaggerParser

#设置输出格式
LOG_FILE = './output/test.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 1024*1024, backupCount = 5) # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
formatter = logging.Formatter(fmt)   # 实例化formatter
handler.setFormatter(formatter)      # 为handler添加formatter
logger = logging.getLogger('tst')    # 获取名为tst的logger
logger.addHandler(handler)           # 为logger添加handler

logger.setLevel(logging.INFO)


#生成request参数的函数
def get_request_args(path, action, swagger_parser):
    """
    :param path: 一个包含action的path，例如user/getUserById
    :param action: post/delete/get/put中的一种方法
    :param swagger_parser: 处理Swagger文档的一个解析器实例，将文档中各个部分分隔开
    :return: 一组可以通过client传输到服务器上的参数
    """
    request_args = {}
    if path in swagger_parser.paths.keys() and action in swagger_parser.paths[path].keys():
        operation_spec = swagger_parser.paths[path][action]
        #查找在operation_spec中的键字"parameters",即swagger文档中用于描述参数的项
        if 'parameters' in operation_spec.keys():
            for param_name, param_spec in operation_spec['parameters'].items():
                #利用函数get_example_from_prop_spec来根据类型获取一些测试参数，这些参数是已经定义好的，返回两组
                request_args[param_name] = swagger_parser.get_example_from_prop_spec(param_spec)

    return request_args

#从配置文件中读取参数的值
def get_args_from_example(path, action, swagger_parser):
    request_args = {}
    if path in swagger_parser.paths.keys() and action in swagger_parser.paths[path].keys():
        operation_spec = swagger_parser.paths[path][action]
        #查找在operation_spec中的键字"parameters",即swagger文档中用于描述参数的项
        if 'parameters' in operation_spec.keys():
            for param_name in operation_spec['parameters'].keys():
                if 'required' in operation_spec['parameters'][param_name] and operation_spec['parameters'][param_name]['required'] > 0:
                    #从不同的配置文件（函数）读取参数
                    request_args[param_name] = param_generator.instagram_example()[param_name]
    return request_args




#验证definition中response的函数
def validate_petstore_definition(swagger_parser, valid_response, response):
    """
    :param swagger_parser: 处理Swagger文档的一个解析器实例，将文档中各个部分分隔开
    :param valid_response: Swagger文档中定义的有效的response
    :param response: request返回的response
    :return: true or false
    """
    #如果没有收到response或者文档中没有说明response
    if response is None or response == '':
        assert valid_response == '' or valid_response is None
        return

    if valid_response == '' or valid_response is None:
        #assert response is None or response == ''
        return

    #返回的是一个list的情况
    if isinstance(valid_response, list):
        assert isinstance(response, list)
        if response:
            valid_response = valid_response[0]
            response = response[0]
        else:
            return

    #当返回值不是dict类型
    if ((not isinstance(response, dict) or not isinstance(valid_response, dict)) and
            (not isinstance(response, (six.text_type, six.string_types)) or
                 not isinstance(valid_response, (six.text_type, six.string_types)))):
        if 'object' not in valid_response:    #应对返回只说明类型是obejct，没有详细说明的情况
            assert type(response) == type(valid_response)
    elif isinstance(response, dict) and isinstance(valid_response, dict):
        #利用swagger_parser提供的函数，在spec中寻找能够匹配的response
        try:
            assert len(set(swagger_parser.get_dict_definition(valid_response, get_list=True))
                       .intersection(swagger_parser.get_dict_definition(response, get_list=True))) >= 1
        except:
            return
        #分别寻找两个response的集合的交来区分是否匹配

#验证返回值的类型是否与文档描述一致
def validate_obj_type(response_data, valid_response_data, inter_dict):
    #有多个object嵌套的情况，因此写成递归的形式
    for k in inter_dict.keys():
        if isinstance(response_data[k], dict):   #如果返回的是一个封装的对象，验证对象的内部
            for _k in response_data[k].keys():
                if isinstance(response_data[k][_k], dict):
                    try:
                        assert _k in valid_response_data[k]
                    except AssertionError:
                        logger.info(u'{0}{1}'.format('Undefined response parameters in Swagger Spec:', k + ':' + _k))
                        print (u'{0}{1}'.format('Undefined response parameters in Swagger Spec:', k + ':' + _k))
                    else:
                        validate_obj_type(response_data[k][_k], valid_response_data[k][_k], valid_response_data[k][_k])   #inter_dict中有键无值
                else:
                    if _k not in valid_response_data[k]:
                        try:
                            assert _k in valid_response_data[k]
                        except AssertionError:
                            logger.info(u'Got parameter name error in spec:{0}'.format(_k))
                            print(u'Got parameter name error in spec:{0}'.format(_k))
                    else:
                        try:
                            assert type(response_data[k][_k]) == type(valid_response_data[k][_k])
                        except AssertionError as exc:
                            logger.info(u'Got type error:{0},should be {1}, but is {2}'.format(_k, type(valid_response_data[k][_k]), type(response_data[k][_k])))
                            print(u'Got type error:{0},should be {1}, but is {2}'.format(_k, type(valid_response_data[k][_k]), type(response_data[k][_k])))
        else:
            try:
                assert type(response_data[k]) == type(valid_response_data[k])
            except AssertionError as exc:
                logger.info(u'Got type error:{0},should be {1}, but is {2}'.format(k, type(valid_response_data[k]), type(response_data[k])))
                print(u'Got type error:{0},should be {1}, but is {2}'.format(k, type(valid_response_data[k]), type(response_data[k])))
    return

def validate_ins_definition(swagger_parser, valid_response, response):
    if isinstance(response['data'], list) and len(response['data']) > 0:
        response_data = response['data'][0] #将list转化为dict类型
    #没有返回数据的情况。只有一个标示操作成功的bool值
    elif response['data'] is None:
        return True
    else:
        response_data = response['data']
    if isinstance(valid_response, list) and len(valid_response) > 0:
        valid_response_data = valid_response[0]
    else:
        valid_response_data = valid_response


    inter_dict = dict.fromkeys(k for k in response_data if k in valid_response_data)    #求两个字典的交集
    #判断返回值的类型是否一致
    validate_obj_type(response_data, valid_response_data, inter_dict)

    ret_dict = dict.fromkeys(k for k in response_data if k not in valid_response_data)    #求两个字典的差集，即返回的数据中多出来的没有在文档中体现的值
    res_ret_dict = dict.fromkeys(k for k in valid_response_data if k not in response_data)    #求两个字典的差集，即返回的数据中缺少的值

    #根据交集和差集的情况对返回值一致性进行判断
    if len(ret_dict) > 0: #返回值没有在文档中定义的情况
        logger.info(u'{0}{1}'.format('Undefined response parameters in Swagger Spec:',ret_dict.keys()))
        print (u'{0}{1}'.format('Undefined response parameters in Swagger Spec:',ret_dict.keys()))
    if len(res_ret_dict) > 0:
        logger.info(u'{0}{1}'.format('Missing parameters in response:',res_ret_dict.keys()))
        print (u'{0}{1}'.format('Missing parameters in response:',res_ret_dict.keys()))

    if len(ret_dict) > 0 or len(res_ret_dict) > 0:
        return True
    return False

def validate_uber_definition(swagger_parser, valid_response, response):
    if isinstance(response, list) and len(response) > 0:
        response = response[0]
    if isinstance(valid_response, list):
        valid_response = valid_response[0]
    if response is None or valid_response is None:
        return True

    inter_dict = dict.fromkeys(k for k in response if k in valid_response)    #求两个字典的交集
    #判断返回值的类型是否一致
    validate_obj_type(response, valid_response, inter_dict)

    ret_dict = dict.fromkeys(k for k in response if k not in valid_response)    #求两个字典的差集，即返回的数据中多出来的没有在文档中体现的值
    res_ret_dict = dict.fromkeys(k for k in valid_response if k not in response)    #求两个字典的差集，即返回的数据中缺少的值

    #根据交集和差集的情况对返回值一致性进行判断
    if len(inter_dict) == 0:    #交集为空，说明返回值和文档中定义的数据结构不同，导致对比失败,可进行进一步对比,思路就是遍历返回的值，将值类型为list或者dict的键找出来对比
        logger.info(u'Data structure of response is different from Swagger Spec!')
        print (u'Data structure of response is different from Swagger Spec!')
    if len(ret_dict) > 0: #返回值没有在文档中定义的情况
        logger.info(u'{0}{1}'.format('Undefined response parameters in Swagger Spec:',ret_dict.keys()))
        print (u'{0}{1}'.format('Undefined response parameters in Swagger Spec:',ret_dict.keys()))
    if len(res_ret_dict) > 0:
        logger.info(u'{0}{1}'.format('Missing parameters in response:',res_ret_dict.keys()))
        print (u'{0}{1}'.format('Missing parameters in response:',res_ret_dict.keys()))

    if len(ret_dict) > 0 or len(res_ret_dict) > 0:
        return True
    return False


def validate_youku_definition(swagger_parser, valid_response, response):

    inter_dict = dict.fromkeys(k for k in response if k in valid_response)    #求两个字典的交集
    ret_dict = dict.fromkeys(k for k in response if k not in valid_response)    #求两个字典的差集，即返回的数据中多出来的没有在文档中体现的值
    res_ret_dict = dict.fromkeys(k for k in valid_response if k not in response)    #求两个字典的差集，即返回的数据中缺少的值

    return


#对生成的参数进行处理，使之能够作为request发送
def parse_parameters(url, action, path, request_args, swagger_parser):
    """
    :param url: url of request
    :param action: HTTP action
    :param path: path of request
    :param request_args: get_request_args函数中生成的参数，是一个dict
    :param swagger_parser: 同上
    :return: (url, body, query_params, headers, files),根据参数输入的类型将值传回去,再取对应的值
    """
    body = None
    query_params = {}
    files = {}
    headers = [('Content-Type', 'application/json')]

    if path in swagger_parser.paths.keys() and action in swagger_parser.paths[path].keys() and len(request_args)>=1:
        operation_spec = swagger_parser.paths[path][action]

        for parameter_name, parameter_spec in operation_spec['parameters'].items():
            #如果参数传递方式为body,直接将值赋给body
            if 'required' in parameter_spec and parameter_spec['required']:
                if parameter_spec['in'] == 'body':
                    body = request_args[parameter_name]
                #如果参数in；的值为path，对url进行处理
                elif parameter_spec['in'] == 'path':
                    url = url.replace('{{{0}}}'.format(parameter_name), str(request_args[parameter_name]))
                #如果参数in:的值为query
                elif parameter_spec['in'] == 'query':
                    if isinstance(request_args[parameter_name], list):
                        #如果是list的话，将每个参数用逗号隔开
                        query_params[parameter_name] = ','.join(request_args[parameter_name])
                    else:
                        #否则直接转换为字符串
                        query_params[parameter_name] = str(request_args[parameter_name])
                #如果参数in:的值为formData
                elif parameter_spec['in'] == 'formData':
                    if body is None:
                        body = {}
                    #如果参数类型为元组，将之赋值给files
                    if (isinstance(request_args[parameter_name], tuple) and
                            hasattr(request_args[parameter_name][0], 'read')):
                        files[parameter_name] = (request_args[parameter_name][1],
                                                 request_args[parameter_name][0])
                    else:
                        body[parameter_name] = request_args[parameter_name]

                    #定义header。第一个header总是有Content-Type, 直接覆盖就行了
                    headers[0] = ('Content-Type', 'multipart/form-data')
                elif parameter_spec['in'] == 'header':
                    #header是否有默认值
                    header_value = parameter_spec['default'] if 'default' in parameter_spec.keys() else ''
                    headers += [(parameter_spec['name'], header_value)]
    return url, body, query_params, headers, files


def get_url_body_from_request(action, path, request_args, swagger_parser):
    """生成url和内容的函数
    :param action: HTTP四大操作
    :param path: 操作所在的路径名
    :param request_args: 通过函数生成的测试参数
    :param swagger_parser: 同上
    :return: (url, body, headers, files)
    """
    #将parser中的basepath和传进来的path组合起来作为url
    url = u'{0}{1}'.format(swagger_parser.base_path, path)
    #得到处理过的参数
    url, body, query_params, headers, files = parse_parameters(url, action, path, request_args, swagger_parser)
    #url?param的格式
    url = '{0}?{1}'.format(url, urlencode(query_params))
    #视情况在url末尾加入access_token,由于instagram所有的action均需要access_token参数，但是有?+access_token和&+access_token两种形式

    if 'shoutaro_010' in url:
        url = url + '&access_token=2027730041.7fbdb00.bee5dd2903584453a399a93d93a5c82d' #ins
    elif url[len(url)-1] == '?':
        url = url + 'access_token=2027730041.7fbdb00.bee5dd2903584453a399a93d93a5c82d' #ins
        #url = url + 'access_token=2.00DZF25D0VoLUHd3b86d0341gT8NxC' #微博

    else:
        url = url + '?access_token=2027730041.7fbdb00.bee5dd2903584453a399a93d93a5c82d' #ins
        #url = url + '?access_token=2.00DZF25D0VoLUHd3b86d0341gT8NxC' #微博

    #对header进行处理
    if ('Content-Type', 'multipart/form-data') not in headers:
        try:
            body = json.dumps(body)  #使用dumps函数对数据进行编码
        except TypeError as exc:
            logger.warning(u'Cannot decode body: {0}.'.format(repr(exc)))
    else:
        headers.remove(('Content-Type', 'multipart/form-data'))

    return url, body, headers, files

#根据不同的访问方法动态生成本地客户端
def get_method_from_action(client, action):
    """根据action的类型生成client
    :param client: flask client
    :param action: 操作类型
    :return: 生成的client
    """
    if action == 'get':
        return client.get
    elif action == 'post':
        return client.post
    elif action == 'put':
        return client.put
    elif action == 'delete':
        return client.delete
    elif action == 'patch':
        return client.patch


def swagger_test(swagger_yaml_path=None, app_url=None, authorize_error=None,
                 wait_between_test=False, use_example=True):
    """对文档进行测试的函数
    :param swagger_yaml_path: swagger文档的路径
    :param app_url: swagger文档的地址
    :param authorize_error: 忽略的状态码
    :param wait_between_test: 测试每个API的时间间隔，防止访问过快而被网站视为恶意访问
    :param use_example: 可以用自己准备的use_example代替自动生成的参数
    :return: 无
    """
    #为了使循环更有效率，我们将函数的主体写在swagger_test_yield函数中,swagger_test_yield的参数与此函数相同
    for _ in swagger_test_yield(swagger_yaml_path=swagger_yaml_path,
                                app_url=app_url,
                                authorize_error=authorize_error,
                                wait_between_test=wait_between_test,
                                use_example=use_example):
        pass

def get_action_from_path(swagger_parser):
    path_operation_sorted = {'post': [], 'get': [], 'put': [], 'patch': [], 'delete': []}
    for key, value in swagger_parser.paths.items():
        if 'post' in value:
            path_operation_sorted['post'].append((key, u'post'))
        if 'get' in value:
            path_operation_sorted['get'].append((key, u'get'))
        if 'put' in value:
            path_operation_sorted['put'].append((key, u'put'))
        if 'patch' in value:
            path_operation_sorted['patch'].append((key, u'patch'))
        if 'delete' in value:
            path_operation_sorted['delete'].append((key, u'delete'))

    return path_operation_sorted


def swagger_test_yield(swagger_yaml_path=None, app_url=None, authorize_error=None,
                       wait_between_test=False, use_example=True):

    if authorize_error is None:
        authorize_error = {}


    #本地文件的情况
    if swagger_yaml_path is not None:
        app_client = requests
        swagger_parser = SwaggerParser(swagger_path=swagger_yaml_path,use_example=True)

    #url的情况
    elif app_url is not None:
        #使用requests提供的默认client
        app_client = requests
        #只需要/.json前面的url
        swagger_parser = SwaggerParser(swagger_dict=requests.get(u'{0}/swagger.json'.format(app_url)).json(),
                                       use_example=True)

        swagger_parser.definitions_example.get('Pet')
    else:
        raise ValueError('You must either specify a swagger.yaml path or an app url')

    operation_sorted = {'post': [], 'get': [], 'put': [], 'patch': [], 'delete': []}

    #将操作排序,operation.items存在的前提是swagger文档中每个操作均有operationID，所以要先做判断是否存在operaionid,但是无法应对有些有id有些无的情况。
    if len(swagger_parser.operation.items()) > 0:
        flag = 0
        for operation, request in swagger_parser.operation.items():
            operation_sorted[request[1]].append((operation, request))
    else:
        flag = 1
        operation_sorted = get_action_from_path(swagger_parser)

    postponed = []

    #记录测试的API数目
    test_no = 0
    #将测试信息输出到excel表格中
    excel_headers = ('No.', 'path', 'action', 'status_code', 'inconsisdency', 'error_info')
    excel_dataset = tablib.Dataset()
    excel_dataset.headers = excel_headers

#按上面的顺序对各个方法进行测试
    for action in ['post', 'get', 'put', 'patch', 'delete']:
        for operation in operation_sorted[action]:
            if flag == 0:
                #operation_sorted以键值对的形式分别存储操作的路径和操作类型：key=operationid,value=(path, action, tag)
                path = operation[1][0]
                action = operation[1][1]
            if flag == 1:
                #以键值对的形式存储：key=path, value=action
                path = operation[0]
                action = operation[1]


            #调用函数得到自动生成的参数#####################################################
            #request_args = get_args_from_example(path, action, swagger_parser)
            request_args = get_args_from_example(path, action, swagger_parser)
            #处理url
            url, body, headers, files = get_url_body_from_request(action, path, request_args, swagger_parser)

            #将测试的信息输出到控制台
            logger.info(u'TESTING {0} {1}'.format(action.upper(), url))
            print(u'TESTING {0} {1}'.format(action.upper(), url))

            #两种client参数有区别
            if swagger_yaml_path is not None:
                my_url = u'{0}{1}'.format('https://' + swagger_parser.host, url)    #应该替换为swagger_parser.schemes
                response = get_method_from_action(app_client, action)(my_url,
                                                                      headers=dict(headers),
                                                                      data=body,
                                                                      files=files)
            ###################################### url ###########
            else:
                my_url = u'{0}{1}'.format('https://' + swagger_parser.host, url)
                response = get_method_from_action(app_client, action)(my_url,
                                                                      headers=dict(headers),
                                                                      data=body,
                                                                      files=files)

            #直接访问response的status_code方法得到状态码
            logger.info(u'Got status code: {0}'.format(response.status_code))
            print(u'Got status code: {0}'.format(response.status_code))

            #检查得到的状态码是不是authorize error中定义的
            if (action in authorize_error and path in authorize_error[action] and
                        response.status_code in authorize_error[action][path]):
                logger.info(u'Got authorized error on {0} with status {1}'.format(url, response.status_code))
                print(u'Got authorized error on {0} with status {1}'.format(url, response.status_code) )
                yield (action, operation)
                continue

            if not response.status_code == 404:
                #得到request的内容
                body_req = swagger_parser.get_send_request_correct_body(path, action)
                #错误处理
                try:
                    response_spec = swagger_parser.get_request_data(path, action, body_req)
                except (TypeError, ValueError) as exc:
                    logger.warning(u'Error in the swagger file: {0}'.format(repr(exc)))
                    print(u'Error in the swagger file: {0}'.format(repr(exc)) + '\n')
                    continue

                #分析response得到其中的数据
                if hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = response.data

                #将得到的response放入json中
                if hasattr(response_text, 'decode'):
                    response_text = response_text.decode('utf-8')


                try:
                    response_json = json.loads(response_text)
                except ValueError:
                    response_json = response_text

                #大于400的状态码统一视作错误
                #assert response.status_code < 400

                if response.status_code in response_spec.keys():
                    inconsisdency = validate_ins_definition(swagger_parser, response_spec[response.status_code], response_json)
                elif 'default' in response_spec.keys():
                    inconsisdency = validate_ins_definition(swagger_parser, response_spec['default'], response_json)
                #所有状态码【200】 都视为正确的返回,如果没有写200的参数，那么默认返回没有参数，而是一个标示操作成功的bool
                elif response.status_code is 200:
                    logger.info('Got status code 200, but undefined in spec.')
                    print('Got status code 200, but undefined in spec.\n')
                elif response.status_code is 405:
                    logger.info('Got status code 405. Method Not Allowed')
                else:
                    logger.info(u'Got status code:{0},parameters error or authorization error.'.format(response.status_code))


                if response.status_code == 200:
                    test_no += 1
                    if inconsisdency:
                        excel_dataset.append([test_no, path, action, response.status_code, 'Yes', '-'])
                    else:
                        excel_dataset.append([test_no, path, action, response.status_code, 'No', '-'])
                else:
                    test_no += 1
                    #excel_dataset.append([test_no, path, action, response.status_code, '-', response.reason])
                    excel_dataset.append([test_no, path, action, response.status_code, '-', response.content])


                if wait_between_test:  # Wait
                    time.sleep(2)
                yield (action, operation)
            else:
                #得到404错误，等待后重试
                if {'action': action, 'operation': operation} in postponed:
                    #如果已经重试过了，报错
                    logger.info(u'Path {0} has been modified or removed!'.format(path))
                    test_no += 1
                    excel_dataset.append([test_no, path, action, response.status_code, '-', response.reason])
                    postponed.remove({'action': action, 'operation': operation})
                else:
                    #将没有重试过的方法放到测试队列最后
                    operation_sorted[action].append(operation)
                    #同时标记为已经推迟过
                    postponed.append({'action': action, 'operation': operation})
                yield (action, operation)
                continue

    excel_dataset.title = 'test_result'
    #导出到Excel表格中
    excel_file = open('./output/test_excel.xlsx', 'wb')
    excel_file.write(excel_dataset.xlsx)
    excel_file.close()

authorize_error = {
    'post': {

    },
    'put': {

    },
    'delete': {

    }
}


swagger_test(swagger_yaml_path='./input/swagger-ins.json',authorize_error=authorize_error)
#swagger_test(swagger_yaml_path='./input/swagger-petstore.yaml',authorize_error=authorize_error)
#swagger_test(app_url='http://petstore.swagger.io/v2',authorize_error=authorize_error)
#swagger_test(app_url='https://apis-guru.github.io/api-models/instagram.com/1.0.0',authorize_error=authorize_error)
