#!/usr/bin/python3

# Copyright (C) 2021 Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Script Remix (BrewPi-Script-RMX).
#
# BrewPi Script RMX is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# BrewPi Script RMX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BrewPi Script RMX. If not, see <https://www.gnu.org/licenses/>.

import git
import os
import json
from pprint import pprint as pp

import BrewPiUtil as util


class GitInfo:
    path = None
    repo = None

    def __init__(self, arg):
        self.path = arg
        self.repo = git.Repo(self.path, search_parent_directories=True)

    def get_git_root(self) -> str:
        try:
            root = self.repo.git.rev_parse("--show-toplevel")
        except:
            root = None
        return root

    def get_git_tag(self) -> str:
        try:
            tags = sorted(self.repo.tags, key=lambda t: t.commit.committed_datetime)
            tagref = str(tags[-1])
        except:
            tagref = None
        return tagref

    def get_git_branch(self) -> str:
        try:
            branch = str(self.repo.active_branch)
        except:
            branch = None
        return branch

    def get_commit_author(self) -> str:
        try:
            name = self.repo.head.commit.author.name
        except:
            name = None
        return name

    def get_commit_author_email(self) -> str:
        try:
            email = self.repo.head.commit.author.email
        except:
            email = None
        return email

    def get_commit_hash(self, length = None) -> str:
        try:
            if length == None:
                commithash = self.repo.head.commit.hexsha
            else:
                commithash = self.repo.head.commit.hexsha[:length]
        except:
            hash = None
        return commithash

    def get_commit_message(self) -> str:
        try:
            message = self.repo.head.commit.message
            message = message.split('\n', 1)[0]
            message = message[ 0 : 50 ].strip()
        except:
            message = None
        return message

    def get_git_dict(self) -> dict:
        git_dict = {}
        git_dict['git_root'] = self.get_git_root()
        git_dict['git_tag'] = self.get_git_tag()
        git_dict['git_branch'] = self.get_git_branch()
        git_dict['commit_author'] = self.get_commit_author()
        git_dict['commit_author_email'] = self.get_commit_author_email()
        git_dict['commit_hash'] = self.get_commit_hash()
        git_dict['commit_hash_short'] = self.get_commit_hash(7)
        git_dict['commit_message'] = self.get_commit_message()
        return git_dict

    def get_git_json(self, ind = None) -> str:
        if ind == None:
            json_str = json.dumps(self.get_git_dict())
        else:
            json_str = json.dumps(self.get_git_dict(), indent = ind)
        return json_str


if __name__ == "__main__":
    config = util.readCfgWithDefaults()
    path_list = [config['toolPath'], config['scriptPath'], config['wwwPath']]
    for path in path_list:
        # need path
        gi = GitInfo(path)
        print("Testing git information for {}".format(path))
        print("Repo = {}".format(gi.get_git_root()))
        print("Tag = {}".format(gi.get_git_tag()))
        print("Branch = {}".format(gi.get_git_branch()))
        print("Commit Hash = {}".format(gi.get_commit_hash()))
        print("Short Commit Hash = {}".format(gi.get_commit_hash(7)))
        print("Commit Author = {}".format(gi.get_commit_author()))
        print("Commit Author Email = {}".format(gi.get_commit_author_email()))
        print("Commit Message = {}".format(gi.get_commit_message()))
        print("Dict object:")
        pp(gi.get_git_dict())
        print("JSON Beacon:")
        print(gi.get_git_json())
        print("JSON Beacon Pretty:")
        print(gi.get_git_json(4))
        print()
