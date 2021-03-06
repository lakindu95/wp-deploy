import json
import os
from colorama import *
from tqdm import tqdm
import ftplib
import pysftp
import getpass
import paramiko
import warnings
warnings.filterwarnings("ignore")


class File:
    def __init__(self):
        init()
        ignore_list = ['site.zip', '', 'deploy-config.json']

    def fetch_old_config(self):
        # Fetches old WP Configurations from wp-config.php
        configs = {}
        data = []
        keys = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'table_prefix']
        filename = "wp-config.php"
        file = open(filename)
        for line in file:
            if "define" in line:
                data = line.split("'")
                if data[1] in keys:
                    configs[data[1]] = data[3]
            elif "$" in line:
                data = line[1:].split("  = ")
                configs[data[0].upper()] = data[1][1:-3]
        file.close()
        return configs

    def prompt_config(self,new_config={}):
        # Prompts user to enter new configurations info
        old_config = self.fetch_old_config()
        if new_config == {}:
            new_config = {}
            print("Please input the following details or press enter to keep old values...")
            print(Style.BRIGHT)
            new_config['db_host'] = input("DB Host Name - Local(Old Value:'" + old_config['DB_HOST'] + "'): ")
            new_config['db_name'] = input("Local Database Name (Old Value:'" + old_config['DB_NAME'] + "'): ")
            new_config['db_user'] = input("Local DB User Name (Old Value:'" + old_config['DB_USER'] + "'): ")
            new_config['db_password'] = getpass.getpass("Local DB Password (Old Value:'" + old_config['DB_PASSWORD'] + "'): ")
            new_config['remote_db_host'] = input("Remote DB Host Name : ")
            new_config['remote_db_user'] = input("Remote DB User Name : ")
            new_config['remote_db_password'] = getpass.getpass("Remote DB Password : ")
            new_config['localhost_url'] = input("Localhost site URL (FORMAT: http://localhost/site_name) : ")
            new_config['site_url'] = input("Remote Site URL (FORMAT: http://www.example.com) : ")
            new_config['sshhostname'] = input("Remote Server IP Address / URL : ")
            new_config['sshuser'] = input("Remote Server user name: ")
            new_config['sshpassword'] = getpass.getpass("Remote Server password : ")
            new_config['ftphostname'] = input("FTP Host Name: ")
            new_config['ftp_user'] = input("FTP Username : ")
            new_config['ftp_pass'] = getpass.getpass("FTP Password : ")
            new_config['remote_dir_path'] = input("Remote Directory path to transfer files (FORMAT: /var/www/html/) :")
            new_config['table_prefix'] = old_config['TABLE_PREFIX']
            print(Style.RESET_ALL)

        return old_config, new_config

    def create_config(self, new_config={}):
        # Creates deploy-config.json file to use in deployment stage
        # Returns 1 if config created successfully ELSE 0
        strings = {'db_host': 'Local Host Name', 'db_name': "Database Name", 'db_user': "Database User Name",
                   'db_password': "Database Password", 'remote_db_host': "Remote DB Host Name",
                   'remote_db_user': "Remote DB User Name", 'remote_db_password': "Remote DB Password",
                   'localhost_url': "Localhost site URL (eg: localhost/site_name", 'site_url': "Remote Site URL",
                   'sshhostname': 'Remote Server IP Address / URL', 'sshuser': "Remote Server user name",
                   'sshpassword': "Remote Server password", "ftp_user": "FTP User name", 'ftphostname': "FTP Host Name",
                   "ftp_pass": "FTP Password", 'remote_dir_path': "Remote Directory path",
                   'table_prefix': "Table Prefix"}
        is_completed = 0
        old_config={}
        if old_config == self.fetch_old_config() and new_config == {}:
            old_config, new_config = self.prompt_config()
            for key, value in new_config.items():
                if value == "":
                    try:
                        new_config[key] = old_config[key.upper()]  # getting values from old configs
                        is_completed = 1
                    except:
                        print(Fore.RED + Back.WHITE + "\n" + strings[
                            key] + " is missing to continue the process. Please re-enter them\n" + Fore.RESET + Back.RESET)

                        is_completed = 0
                        break
        else:
            is_completed = 1
        if is_completed:
            file = open("deploy-config.json", "w")
            file.write(json.dumps(new_config))
            file.close()
            print("Config Created")
            return 1
        else:
            return 0


    def changewpconfig(self):
        print("Changing wp-config file")
        configfile = open("deploy-config.json", "r")
        wpfile = open("wp-config.php", 'r')

        configs = json.loads(configfile.readlines()[0])
        lines = wpfile.readlines()
        wpfile.close()
        for line in lines:
            if line.startswith("define('DB_NAME'"):
                lines[lines.index(line)] = "define('DB_NAME', '" + configs['db_name'] + "');\n"
            elif line.startswith("define('DB_USER'"):
                lines[lines.index(line)] = "define('DB_USER', '" + configs['remote_db_user'] + "');\n"
            elif line.startswith("define('DB_PASSWORD'"):
                lines[lines.index(line)] = "define('DB_PASSWORD', '" + configs['remote_db_password'] + "');\n"

        wpfile = open("wp-config.php", 'w')
        wpfile.writelines(lines)
        wpfile.close()
        configfile.close()

    def resetwpconfig(self):
        print("Changing wp-config file")
        configfile = open("deploy-config.json", "r")
        wpfile = open("wp-config.php", 'r')

        configs = json.loads(configfile.readlines()[0])
        lines = wpfile.readlines()
        wpfile.close()
        for line in lines:
            if line.startswith("define('DB_NAME'"):
                lines[lines.index(line)] = "define('DB_NAME', '" + configs['db_name'] + "');\n"
            elif line.startswith("define('DB_USER'"):
                lines[lines.index(line)] = "define('DB_USER', '" + configs['db_user'] + "');\n"
            elif line.startswith("define('DB_PASSWORD'"):
                lines[lines.index(line)] = "define('DB_PASSWORD', '" + configs['db_password'] + "');\n"

        wpfile = open("wp-config.php", 'w')
        wpfile.writelines(lines)
        wpfile.close()
        configfile.close()

    def ftp_transfer(self, host, username, password, remote_dir_path):
        root_dir = os.getcwd()
        ftp = ftplib.FTP(host, username, password)
        ignore_list = ['deploy-config.json']
        print("Transferring Files to "+host)
        for dirName, subdirList, fileList in os.walk(root_dir):
            if os.path.isdir(os.path.relpath(dirName)):
                try:
                    ftp.mkd(os.path.join(remote_dir_path, os.path.relpath(dirName).replace("\\", "/")))
                except:
                    pass
            for fname in fileList:
                file_path = os.path.join(dirName, fname)
                filesize = os.path.getsize(file_path)
                file = open(file_path, 'rb')
                if fname not in ignore_list:
                    with tqdm(unit='blocks', unit_scale=True, leave=False, miniters=1, desc=fname,
                              total=filesize) as tqdm_instance:
                        if os.path.isdir(os.path.relpath(dirName)):
                            ftp.storbinary(
                                'STOR ' + os.path.join(remote_dir_path, os.path.relpath(dirName), fname).replace("\\", "/"),
                                file, 2048, callback=lambda sent: tqdm_instance.update(len(sent)))
                        else:
                            ftp.storbinary('STOR ' + os.path.join(remote_dir_path, fname), file, 2048,
                                           callback=lambda sent: tqdm_instance.update(len(sent)))
        print("File Transfer to "+host+" Completed:)")

    def sftp_transfer(self, host, username, password, remote_dir_path):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        srv = pysftp.Connection(host=host, username=username, password=password, cnopts=cnopts)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password)

        root_dir = os.getcwd()
        ignore_list = ['deploy-config.json']
        print("Transferring files to "+host)
        for dirName, subdirList, fileList in os.walk(root_dir):
            if os.path.isdir(os.path.relpath(dirName)):
                exec_code = "mkdir "+os.path.join(remote_dir_path, os.path.relpath(dirName)).replace("\\", "/")
                stdin, stdout, stderr = ssh.exec_command(exec_code)

            for fname in fileList:
                file_path = os.path.join(dirName, fname)
                filesize = os.path.getsize(file_path)
                if fname not in ignore_list:
                    with tqdm(unit='blocks', unit_scale=True, leave=False, miniters=1, desc=fname,
                              total=filesize) as tqdm_instance:
                        if os.path.isdir(os.path.relpath(dirName)):
                            srv.put(file_path,
                                    os.path.join(remote_dir_path, os.path.relpath(dirName), fname).replace("\\", "/"),
                                    callback=lambda sent, total: tqdm_instance.update(sent))
                        else:
                            srv.put(file_path, os.path.join(remote_dir_path, fname),
                                    callback=lambda sent, total: tqdm_instance.update(sent))

        print("File Transfer to " + host + " Completed:)")

