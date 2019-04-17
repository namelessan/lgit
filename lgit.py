#!/usr/bin/env python3
from utils import *


def main():
    args = getArgs()
    # print(args)
    if args.command == 'init':
        if args.init_dir:
            initGit(args.init_dir)
        else:
            initGit()
    else:
        lgit_parent_path = getGitParentPath()
        if lgit_parent_path is None:
            print('fatal: not a git repository\
 (or any of the parent directories)')
        else:
            lgit_path = path.join(getGitParentPath(), '.lgit')
            if args.command == 'add':
                for item_path in args.files:
                    if path.isfile(item_path):
                        addGitFile(item_path, lgit_path, lgit_parent_path)
                    elif path.isdir(item_path):
                        addGitDir(item_path, lgit_path, lgit_parent_path)
                    else:
                        print("fatal: pathspec '{}'".format(item_path) +
                              "did not match any files")
            elif args.command == 'commit':
                message = args.message
                if message is None:
                    message = ''
                commitGit(lgit_path, lgit_parent_path, message)
            elif args.command == 'rm':
                for file in args.rm_files:
                    rmGit(file, lgit_path)
            elif args.command == 'config':
                author = args.author
                configGit(author, lgit_path)
            elif args.command == 'status':
                checkGitStt()
            elif args.command == 'ls-files':
                lsFileGit()
            elif args.command == 'log':
                logGit(lgit_path)


if __name__ == '__main__':
    main()
