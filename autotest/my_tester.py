# -*- coding: utf-8 -*-

import json
import logging
import os
import requests
import six
import time

try:
    from urllib import urlencode
except ImportError:  # Python 3
    from urllib.parse import urlencode

import connexion

from swagger_parser import SwaggerParser

#设置输出格式
logging.basicConfig()
logger = logging.getLogger(__name__)
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
                #利用swagger_parser中的函数get_example_from_prop_spec来根据类型自动生成一些测试参数
                request_args[param_name] = swagger_parser.get_example_from_prop_spec(param_spec)

    return request_args

#保存测试的结果
def save_test_result_to_txt(filename, contents):
    fh = open(filename, 'a')
    fh.write(contents)
    fh.close()


#验证definition中response的函数
def validate_definition(swagger_parser, valid_response, response):
    """
    :param swagger_parser: 处理Swagger文档的一个解析器实例，将文档中各个部分分隔开
    :param valid_response: Swagger文档中定义的有效的response
    :param respinse: request返回的response
    :return: true or false
    """
    #如果没有收到response或者文档中没有说明response
    if response is None or response == '':
        assert valid_response == '' or valid_response is None
        return

    if valid_response == '' or valid_response is None:
        assert response is None or response == ''
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
        assert type(response) == type(valid_response)
    elif isinstance(response, dict) and isinstance(valid_response, dict):
       #利用swagger_parser提供的函数，在spec中寻找能够匹配的response
        assert len(set(swagger_parser.get_dict_definition(valid_response, get_list=True))
                   .intersection(swagger_parser.get_dict_definition(response, get_list=True))) >= 1
         #分别寻找两个response的集合的交来区分是否匹配

#对生成的参数进行处理，使之能够发送request
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

    if path in swagger_parser.paths.keys() and action in swagger_parser.paths[path].keys():
        operation_spec = swagger_parser.paths[path][action]

        for parameter_name, parameter_spec in operation_spec['parameters'].items():
             #如果参数in：的值为body,直接将值赋给body
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

                # #定义header。第一个header总是有Content-Type, 直接去掉就行了
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
    #对header进行处理
    if ('Content-Type', 'multipart/form-data') not in headers:
        try:
            body = json.dumps(body)  #使用dumps函数对数据进行编码
        except TypeError as exc:
            logger.warning(u'Cannot decode body: {0}.'.format(repr(exc)))
    else:
        headers.remove(('Content-Type', 'multipart/form-data'))

    return url, body, headers, files


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
    :param use_example: 如果想要进行数据驱动的测试，可以用自己准备的use_example代替自动生成的参数
    :return: 无
    """
    #为了使循环更有效率，我们将函数的主体写在swagger_test_yield函数中,swagger_test_yield的参数与此函数相同
    for _ in swagger_test_yield(swagger_yaml_path=swagger_yaml_path,
                                app_url=app_url,
                                authorize_error=authorize_error,
                                wait_between_test=wait_between_test,
                                use_example=use_example):
        pass


def swagger_test_yield(swagger_yaml_path=None, app_url=None, authorize_error=None,
                       wait_between_test=False, use_example=True):

    if authorize_error is None:
        authorize_error = {}

    #本地文件的情况
    if swagger_yaml_path is not None:
        #如果是相对路径就转化为绝对路径，并且使用connexion这个包的App方法来处理swagger文档
        app = connexion.App(__name__, port=8080, debug=True, specification_dir=os.path.dirname(os.path.realpath(swagger_yaml_path)))
        app.add_api(os.path.basename(swagger_yaml_path))
        #connexion中提供了生成client的方法
        app_client = app.app.test_client()
         #使用swagger_parser处理swagger文档
        swagger_parser = SwaggerParser(swagger_yaml_path, use_example=use_example)

    #url的情况
    elif app_url is not None:
         #使用requests提供的默认client
        app_client = requests
        swagger_parser = SwaggerParser(swagger_dict=requests.get(u'{0}/swagger.json'.format(app_url)).json(),
                                       use_example=False)
    else:
        raise ValueError('You must either specify a swagger.yaml path or an app url')

    operation_sorted = {'post': [], 'get': [], 'put': [], 'patch': [], 'delete': []}

     #将操作排序
    for operation, request in swagger_parser.operation.items():
        operation_sorted[request[1]].append((operation, request))

    postponed = []

    #按上面的顺序对各个方法进行测试
    for action in ['post', 'get', 'put', 'patch', 'delete']:
        for operation in operation_sorted[action]:
            #operation_sorted以二维数组的形式分别存储操作的路径和类型(get/put...)
            path = operation[1][0]
            action = operation[1][1]
            #调用函数得到自动生成的参数
            request_args = get_request_args(path, action, swagger_parser)
            #处理url
            url, body, headers, files = get_url_body_from_request(action, path, request_args, swagger_parser)

            #将测试的信息输出到控制台
            logger.info(u'TESTING {0} {1}'.format(action.upper(), url))
            save_test_result_to_txt('./output/result.txt',u'TESTING {0} {1}'.format(action.upper(), url) + '\n')

            if swagger_yaml_path is not None:
                response = get_method_from_action(app_client, action)(url, headers=headers,
                                                                      data=body)
            else:
                response = get_method_from_action(app_client, action)(u'{0}{1}'.format(app_url.replace(swagger_parser.base_path, ''), url),
                                                                      headers=dict(headers),
                                                                      data=body,
                                                                      files=files)

            #直接访问response的status_code方法得到状态码
            logger.info(u'Got status code: {0}'.format(response.status_code))
            save_test_result_to_txt('./output/result.txt',u'Got status code: {0}'.format(response.status_code) + '\n')

            #检查得到的错误代码是不是authorize error中定义的
            if (action in authorize_error and path in authorize_error[action] and
                    response.status_code in authorize_error[action][path]):
                logger.info(u'Got authorized error on {0} with status {1}'.format(url, response.status_code))
                save_test_result_to_txt('./output/result.txt'u'Got authorized error on {0} with status {1}'.format(url, response.status_code) + '\n')
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
                    save_test_result_to_txt('./output/result.txt',u'Error in the swagger file: {0}'.format(repr(exc)) + '\n')
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
                assert response.status_code < 400

                if response.status_code in response_spec.keys():
                    validate_definition(swagger_parser, response_spec[response.status_code], response_json)
                elif 'default' in response_spec.keys():
                    validate_definition(swagger_parser, response_spec['default'], response_json)
                #所有状态码【200】 都是正确的返回？如果没有写200的参数，如何验证返回的参数是否正确？
                elif response.status_code is 200:
                    logger.info('Got status code 200, but undefined in spec.')
                    save_test_result_to_txt('./output/result.txt','Got status code 200, but undefined in spec.\n')
                else:
                    #得到了不在文档中和自己定义的authorize error中写明的状态码
                    raise AssertionError('Invalid status code {0}. Expected: {1}'.format(response.status_code,
                                                                                         response_spec.keys()))
                    save_test_result_to_txt('./output/result.txt','Invalid status code {0}. Expected: {1}'.format(response.status_code,
                                                                                         response_spec.keys()) + '\n')

                if wait_between_test:  # Wait
                    time.sleep(2)

                yield (action, operation)
            else:
                #得到404错误，等待后重试
                if {'action': action, 'operation': operation} in postponed:
                    #如果已经重试过了，报错
                    raise Exception(u'Invalid status code {0}'.format(response.status_code))

                #将没有重试过的方法放到测试队列最后
                operation_sorted[action].append(operation)
                #同时标记为已经推迟过
                postponed.append({'action': action, 'operation': operation})
                yield (action, operation)
                continue

authorize_error = {
       'post': {

       },
       'put': {

       },
       'delete': {

       }
}

#直接将文档下载下来使用还是会有bug，不知道是connexion的问题还是文档格式的问题，待解决，输入url地址就没问题
#swagger_test(swagger_yaml_path='./input/swagger-twitter.json',authorize_error=authorize_error)
swagger_test(app_url='http://petstore.swagger.io/v2',authorize_error=authorize_error)
