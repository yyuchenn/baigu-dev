from os import walk
from os.path import join, splitext
from random import choice
from repo_model import Repo
from peewee import fn
from git import Git
import requests
from time import sleep

'''
query = Repo.select().where(Repo.archived == False).order_by(fn.Random())

with open("list.txt", "w") as f:
    for repo in query[:384]:
        url = repo.url
        print(url)
        r = Git('./samples')
        r.clone(repo.url)
        python_files = []
        for root, dirs, files in walk(join("./samples", url.split("/")[-1])):
            for name in files:
                if splitext(name)[1] == ".py":
                    python_files.append(join(root, name))
        picked = choice(python_files)
        f.write(picked + "\n")
'''

query = Repo.select().where(Repo.archived == False).order_by(fn.Random())

with open("list_repo.txt", "a") as repo_file:
    with open("list_unittest.txt", "a") as unittest_file:
        with open("list_changed.txt", "a") as changed_file:
            headers = {"Authorization": "Basic eXl1Y2hlbm46Z2hwXzJXNWk3Q3Q4QTNwT0ZTMnQ2SmRKSTVqSzI3bGdmUjE1SGhPag=="}
            i = 0
            completed = 0
            while completed < 384 - 320:
                repo_str = " ".join([f'repo:{q.url.split("/")[-2]+"/"+q.url.split("/")[-1]}' for q in query[i:i+10]])
                params = {"q": f'"import unittest" {repo_str}', "per_page": 100}
                response = requests.get("https://api.github.com/search/code", params=params, headers=headers).json()
                while "total_count" not in response:
                    print(".")
                    sleep(120)
                    response = requests.get("https://api.github.com/search/code", params=params, headers=headers).json()
                found = []
                if response["total_count"] != 0:
                    for item in response["items"]:
                        full_name = item["repository"]["full_name"]
                        if full_name not in found:
                            found.append(full_name)
                            r = Git('./samples_unittest')
                            r.clone(f"https://github.com/{full_name}")
                            python_files = []
                            for root, dirs, files in walk(join("./samples_unittest", full_name.split("/")[-1])):
                                for name in files:
                                    if splitext(name)[1] == ".py":
                                        python_files.append(join(root, name))
                            picked = choice(python_files)
                            repo_file.write(full_name + "\n")
                            changed_file.write(picked + "\n")
                            completed += 1
                        unittest_file.write(join("./samples_unittest", full_name.split("/")[-1], item["path"]) + "\n")
                print(completed)

                i += 10
                sleep(10)
