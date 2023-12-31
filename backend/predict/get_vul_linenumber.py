import subprocess
import os
import time
import json
import re
import path_required

'''
description: 该文件需要设置 C_source_dir、SC_path、sensitive_funcname_txt_path
运行命令: python3 ./get_vul_linenumber
'''

# Joern 运行的 .sc 脚本
SC_path = path_required.SC_path
# txt 文件路径 包含敏感函数名
sensitive_funcname_txt_path = path_required.sensitive_funcname_txt_path


def get_all_function_list(txt_path):
    '''
    description: 将 txt 文件里面的内容提取到一个 function_list 列表
    param {string} txt_path: txt 文件路径
    return {list} function_list: 返回 function_list 列表
    '''

    with open(txt_path, 'r') as txtfile:
        function_list = []
        for line in txtfile.readlines():
            sensitive_funcname = line.strip('\n')
            function_list.append(sensitive_funcname)
    return function_list


def c2res(c_Filename, function_list):
    '''
    description: 使用joern-parse解析一个c文件得到cpg图,对cpg图进行josrn分析,提取可能的漏洞代码和行号,保存在一个json文件
    param {string} c_Filename
    param {list} function_list
    '''
    # c 源文件目录
    single_dir_path = path_required.single_dir_path
    C_source_dir = single_dir_path + '/C_file/'
    with open("a.txt", 'a') as file:
        file.write("begin " + c_Filename + '\n')
    result_file_path = ''
    if '/' in c_Filename:
        str = '/'
        dir_name = str.join(c_Filename.split('/')[:-1])
        c_Filename = c_Filename.split('/')[-1]
    for filepath, dirnames, filenames in os.walk(C_source_dir):
        flag = False
        for item in filenames:
            if c_Filename == item and (dir_name in filepath):
                c_file_path = filepath + '/' + item
                c_file_dir = filepath
                result_filename = c_Filename[:-2] + '_res.json'
                result_file_path = c_file_dir + '/' + result_filename
                # already create json
                if os.path.exists(result_file_path):
                    return result_file_path
                # parse source code into cpg
                print('parsing source code into cpg...')
                print(c_file_path + "\n")
                cpg_filename = c_Filename[:-2] + '.bin'
                shell_command = "joern-parse --output " + cpg_filename + " " + c_file_path
                subprocess.call(shell_command, shell=True)
                # move cpg into .c file dir
                shell_command = "mv -b ./" + cpg_filename + " " + c_file_dir
                subprocess.call(shell_command, shell=True)
                # cpg into json
                json_filename = c_Filename[:-2] + '.json'
                project_filename = c_Filename[:-2] + ".bin"
                json_file_path = c_file_dir + '/' + json_filename
                cpg_file_path = c_file_dir + '/' + cpg_filename
                shell_command = "joern --script " + SC_path + " --params cpgFile=" + \
                                cpg_file_path + ",projectFolder=" + os.path.abspath(project_filename) + \
                                ",outFile=" + json_file_path
                subprocess.call(shell_command, shell=True)
                # json into result
                with open(json_file_path) as file:
                    properties_data = json.load(file)
                shell_command = "rm " + json_file_path
                subprocess.call(shell_command, shell=True)
                shell_command = "rm " + cpg_file_path
                subprocess.call(shell_command, shell=True)
                with open(result_file_path, 'w') as result:
                    allres = []
                    variable_list = []
                    for item in properties_data:
                        if item['_label'] == "LOCAL":
                            variable_list.append(item['name'])
                    for item in properties_data:
                        if ('*' in item['code'] or '[' in item['code']) and item['_label'] == "LOCAL":
                            res = {}
                            var = re.findall(
                                r"[_a-zA-Z][_a-zA-Z0-9]*", item['name'])[0]
                            res['variable'] = var
                            res['lineNumber'] = item['lineNumber']
                            allres.append(res)
                            print(res)
                        elif '<operator>.assignment' == item['name'] and item['_label'] == "CALL":
                            for var in variable_list:
                                if '=' in item['code'] and var in re.split('=', item['code'])[1]:
                                    res = {}
                                    var = re.split('=', item['code'])[0]
                                    var = re.findall(
                                        r"[_a-zA-Z][_a-zA-Z0-9]*", var)[0]
                                    res['assignment'] = var
                                    res['lineNumber'] = item['lineNumber']
                                    allres.append(res)
                                    print(res)
                                    break
                        elif function_list.count(item['name']) != 0 and item['_label'] == "CALL":
                            res = {}
                            res['function'] = item['name'].strip()
                            res['lineNumber'] = item['lineNumber']
                            allres.append(res)
                            print(res)
                    print(allres)
                    json.dump(allres, result)
                    flag = True
                    break
        if flag == True:
            break
    with open("a.txt", 'a') as file:
        file.write("finish " + result_filename + '\n')
    return result_file_path
