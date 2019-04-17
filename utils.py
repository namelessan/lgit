from argparse import ArgumentParser
from os import path, mkdir, walk
from os import environ, getcwd, chdir, listdir, unlink
from shutil import rmtree
from hashlib import sha1
from datetime import datetime


def getArgs():
    parser = ArgumentParser(prog='lgit.py', description=None)
    sub_parsers = parser.add_subparsers(dest='command')

    sub_parsers_init = sub_parsers.add_parser('init')
    sub_parsers_init.add_argument('init_dir', nargs='?')

    sub_parsers_status = sub_parsers.add_parser('status')

    sub_parsers_add = sub_parsers.add_parser('add')
    sub_parsers_add.add_argument('files', nargs='*', help="file to add")

    sub_parsers_rm = sub_parsers.add_parser('rm')
    sub_parsers_rm.add_argument('rm_files', nargs='*', help="file to add")

    sub_parsers_commit = sub_parsers.add_parser('commit')
    sub_parsers_commit.add_argument('-m', dest='message')

    sub_parsers_config = sub_parsers.add_parser('config')
    sub_parsers_config.add_argument('--author', action='store')

    sub_parsers_ls_files = sub_parsers.add_parser('ls-files')

    sub_parsers_log = sub_parsers.add_parser('log')

    args = parser.parse_args()
    return args


def getTimeStamp(filepath, mcr_sec=False):
    '''
    input: filename:path to file; mcr_sec:return time in milisec True or False
    output: time in year, month, day, hour, minute, second format
    '''
    t = path.getmtime(filepath)  # Get modify time of the file
    if mcr_sec:
        # return time format in microsec
        return datetime.fromtimestamp(t).strftime('%Y%m%d%H%M%S.%f')
    else:
        # return time format in sec
        return datetime.fromtimestamp(t).strftime('%Y%m%d%H%M%S')


# Helper Function for initGit to process destination dir recursively
def createDir(dest):
    dest = dest[len(getcwd()) + 1:]
    sub_dirs = dest.split('/')
    sub_path = getcwd()
    # Create new dest dir, check its quality
    for sub_dir in sub_dirs:
        sub_path = path.join(sub_path, sub_dir)
        try:  # If dir is non-existing
            mkdir(sub_path)
        except FileExistsError:  # If dir is existing
            if path.isfile(sub_path):
                dest_name = sub_path.split('/')[-1]
                print('fatal: cannot mkdir {}: File exists'.format(dest_name))
                return False
            else:
                continue
    return True


# Helper function of initGit to create .lgit
def createGitDir(lgit_path):
    # Create new .lgit dir, check its quality
    try:
        mkdir(lgit_path)
    except FileExistsError:  # If .lgit is existing
        if path.isfile(lgit_path):
            print('fatal: Invalid gitfile format:', lgit_path)
            return False
        elif path.isdir(lgit_path):  # If .lgit is a dir
            print("Git repository already initialized.")
    return True


# Helper function of initGit to create subfolders in .lgit
def createGitSubs(lgit_path):
    init_git = {'dir': ('objects', 'commits', 'snapshots'),
                'file': ('index', 'config')}
    # Initialize the .lgit dir
    for dir in init_git['dir']:  # Create dirs: objects, commits, snapshots
        try:
            mkdir(path.join(lgit_path, dir))
        except FileExistsError:
            pass
    for file in init_git['file']:
        try:
            with open(path.join(lgit_path, file), 'x') as f:
                if file == 'config':
                    f.write(environ.get('LOGNAME'))  # Get name of env
        except FileExistsError:
            pass


# lgit init
def initGit(dest=getcwd()):
    '''
    Input: dest
    output: create 3 dir: objects, commits, snapshots
                   2 file: index, config
    '''
    dest = path.join(getcwd(), dest)  # './dest'
    lgit_path = path.join(dest, '.lgit')  # './dest/.lgit'
    if createDir(dest):  # If dest is successfuly created.
        if createGitDir(lgit_path):  # If ./dest/.lgit is successfuly created.
            createGitSubs(lgit_path)


def getSha1(file):
    '''
    input: filepath to get SHA1 code
    output: SHA1 code of the file
    '''
    # BUF_SIZE for everytime read(). Here is set to 64KB
    BUF_SIZE = 65536
    # create a hash object called SHA1
    SHA1 = sha1()
    try:
        # open a file to get SHA1 code
        with open(file, 'rb') as f:
            while True:
                # read everytime 64kb of file
                data = f.read(BUF_SIZE)
                if not data:
                    break
                # reupdate sha1 everytime read the file
                SHA1.update(data)
        # return a 40-chars length sha1
        return SHA1.hexdigest()
    except FileNotFoundError:
        print("fatal: pathspec '{}' did not match any files".format(file))
        pass


# Check if the current working directory is initialized with lgit
def checkInited(lgit_path):
    if not path.isdir(lgit_path):
        return False
    init_git = {'dir': ('objects', 'commits', 'snapshots'),
                'file': ('index', 'config')}
    for dir in init_git['dir']:
        check_path = path.join(lgit_path, dir)
        if not path.isdir(check_path):
            return False
    for file in init_git['file']:
        check_path = path.join(lgit_path, file)
        if not path.isfile(check_path):
            return False
    return True


# Get the path of lgit of current working directory
def getGitParentPath():
    cwd = getcwd()
    parrent_paths = cwd.split('/')
    new_path = ''
    sub_paths = []
    for sub_path in parrent_paths[1:]:
        new_path = path.join(new_path, sub_path)
        sub_paths.append(new_path)
    sub_paths.reverse()  # Reverse the list to check backward.
    for sub_path in sub_paths:
        lgit_parent_path = path.join('/', sub_path)
        # if checkInited(path.join(lgit_parent_path, '.lgit')):
        if path.isdir(path.join(lgit_parent_path, '.lgit')):
            return lgit_parent_path
    return None  # Return None if cwd is not init'ed yet


# Get info of a field (timestamp, current hash,..., file in a line of Index)
def getInfoOfField(index_line, field):
    if field == 0:  # Get timestamp
        return index_line[:14]
    elif field == 1:
        return index_line[15:15+40]
    elif field == 2:
        return index_line[56:56+40]
    elif field == 3:
        return index_line[97:97+40]
    elif field == 4:
        return index_line[138:].strip('\n')


def detectLineOfFile(file, index_content):
    for idx, index_line in enumerate(index_content):
        file_name = getInfoOfField(index_line, 4)
        if file == file_name:
            return idx


# Read the content of a file
def getFileContent(file):
    try:
        with open(file, 'r', errors='ignore') as f:
            data = f.readlines()
        return data
    except FileNotFoundError:
        print("fatal: pathspec '{}' did not match any files".format(file))
        pass


# Write the content to a file
def writeFileContent(file, content):
    with open(file, 'w+') as f:
        f.write(content)


# Append the content to a file
def appendFileContent(file, content):
    try:
        with open(file, 'a+') as f:
            f.write(content)
    except FileNotFoundError:
        print("fatal: pathspec '{}' did not match any files".format(file))
        pass


def updateObjectsWithAdd(lgit_path, file_content, file_hash):
    object_dir_path = path.join(lgit_path, 'objects')
    object_sub_dir_path = path.join(object_dir_path, file_hash[:2])
    try:
        mkdir(object_sub_dir_path)
    except FileExistsError:
        pass
    file_content = ''.join(file_content)
    object_file_path = path.join(object_sub_dir_path, file_hash[2:])
    writeFileContent(object_file_path, file_content)


# lgit add a file
def addGitFile(file, lgit_path, lgit_parent_path):
    index_path = path.join(lgit_path, 'index')
    index_content = getFileContent(index_path)
    file_hash = getSha1(file)
    if index_content is not None and file_hash is not None:
        file_timestamp = getTimeStamp(file)
        file_content = getFileContent(file)
        updateObjectsWithAdd(lgit_path, file_content, file_hash)
        # Update the index file
        abs_file_path = path.abspath(file)
        # If the file not in lgit's parent
        if lgit_parent_path != abs_file_path[:-len(file)-1]:
            file = abs_file_path[len(lgit_parent_path)+1:]
        file_line_idx = detectLineOfFile(file, index_content)
        if file_line_idx is None:
            commit_file_index = ' '*40
            new_file_line = ' '.join([file_timestamp, file_hash, file_hash,
                                      commit_file_index, file])
            appendFileContent(index_path, new_file_line + '\n')
        else:
            commit_file_index = getInfoOfField(index_content[file_line_idx], 3)
            new_file_line = ' '.join([file_timestamp, file_hash, file_hash,
                                      commit_file_index, file])
            index_content[file_line_idx] = new_file_line + '\n'
            new_index_content = ''.join(index_content)
            writeFileContent(index_path, new_index_content)


# Get all the paths in a dir recursively
def getDirRecursively(dir):
    paths = []
    for root, _, files in walk(dir):
        for file in files:
            file_path = path.join(root, file)
            if '.lgit/' not in file_path:
                paths.append(file_path)
    return paths


# lgit add dir
def addGitDir(dir, lgit_path, lgit_parent_path):
    files = getDirRecursively(dir)
    for file in files:
        addGitFile(file, lgit_path, lgit_parent_path)


# Git commit functions
# Get timestamp of the current time.
def getTimeStampNow(mcr_sec=False):
    if mcr_sec:
        return datetime.now().strftime('%Y%m%d%H%M%S.%f')
    else:
        return datetime.now().strftime('%Y%m%d%H%M%S')


# Update the commits dir when lgit commit
def updateCommits(commits_path, file_name, author_name, message):
    now_time = getTimeStampNow()
    content = '\n'.join([author_name, now_time, '', message, ''])
    file_path = path.join(commits_path, file_name)
    writeFileContent(file_path, content)


# Update the snapshots and index when lgit commit
def updateSnapshotsAndIndex(snapshots_path, file_name, index_path):
    index_content = getFileContent(index_path)
    snapshots_file_path = path.join(snapshots_path, file_name)
    is_commited = False
    for idx, index_line in enumerate(index_content):
        timestamp_info = getInfoOfField(index_line, field=0)
        current_info = getInfoOfField(index_line, field=1)
        add_info = getInfoOfField(index_line, field=2)
        commit_info = getInfoOfField(index_line, field=3)
        file_name_info = getInfoOfField(index_line, field=4)
        if add_info != commit_info:
            commit_info = add_info
            is_commited = True
            new_line_content = ' '.join([timestamp_info, current_info,
                                        add_info, commit_info, file_name_info])
            index_content[idx] = new_line_content + '\n'
            snapshots_content = ' '.join([commit_info, file_name_info]) + '\n'
            appendFileContent(snapshots_file_path, snapshots_content)
    if is_commited:
        new_index_content = ''.join(index_content)
        writeFileContent(index_path, new_index_content)
    else:
        print('no changes added to commit')
    return is_commited


# lgit commit
def commitGit(lgit_path, lgit_parent_path, message):
    commits_path = path.join(lgit_path, 'commits')
    snapshots_path = path.join(lgit_path, 'snapshots')
    config_path = path.join(lgit_path, 'config')
    index_path = path.join(lgit_path, 'index')
    config_content = getFileContent(config_path)
    author_name = config_content[-1].strip('\n')
    file_name = getTimeStampNow(mcr_sec=True)
    if updateSnapshotsAndIndex(snapshots_path, file_name, index_path):
        updateCommits(commits_path, file_name, author_name, message)


'''___________________________GIT STATUS_________________________________'''


def updateWithStatus(line, file_path):
    # get 5 field from the line
    field0 = getTimeStamp(file_path)
    field1 = getSha1(file_path)
    field2 = getInfoOfField(line, 2)
    field3 = getInfoOfField(line, 3)
    field4 = getInfoOfField(line, 4)
    # update the line with new field
    replace_line = ' '.join([field0, field1, field2, field3, field4]) + '\n'
    return replace_line


def updateIndex(file_path, mode):
    '''
    input: path of the file to update
    output: update the index file
    '''
    # get path to index file
    index_path = path.join(getGitParentPath(), '.lgit/index')
    # get file name from the path
    file_name = getIndexFileName(file_path)
    print(file_name)
    # idx_content is a list from the index content
    idx_content = getFileContent(index_path)
    # get the line content from the list
    line_idx = detectLineOfFile(file_name, idx_content)
    line = idx_content[line_idx]

    if mode == 'status':
        replace_line = updateWithStatus(line, file_path)
        idx_content[line_idx] = replace_line
    elif mode == 'rm':
        idx_content.remove(line)
    # rewrite all the content of index file
    writeFileContent(index_path, ''.join(idx_content))


def getIndexFileName(file_path):
    '''
    input: file_path: abspath to the file
    output: file_name saved in index file
    '''
    lgit_parent_path = getGitParentPath()
    file_name = file_path[len(lgit_parent_path)+1:]
    return file_name


def isInIndex(file_name, idx_content):
    confirm = False
    for line in idx_content:
        if file_name in line:
            confirm = True
            break
    return confirm


def isTrackedFile(file_path):
    # get path to index file
    index_path = path.join(getGitParentPath(), '.lgit/index')
    # get file name from the path
    file_name = getIndexFileName(file_path)
    # idx_content is a list from the index content
    idx_content = getFileContent(index_path)
    return isInIndex(file_name, idx_content)


def getTrackAndUntrack(file_paths):
    untracked_files = []
    tracked_files = []
    for path in file_paths:
        if isTrackedFile(path):
            tracked_files.append(path)
        else:
            untracked_files.append(path)
    return tracked_files, untracked_files


def isStagedFile(line_idx):
    # get hash of added field
    field2 = getInfoOfField(line_idx, 2)
    # get hash of commited field
    field3 = getInfoOfField(line_idx, 3)
    # if added field and commited field is difference: means staged
    return field2 != field3


def isUnstagedFile(line_idx):
    # get hash of current file
    field1 = getInfoOfField(line_idx, 1)
    # get hash of added field
    field2 = getInfoOfField(line_idx, 2)
    # if hash of current file and added is difference: means unstaged
    return field1 != field2


def getStagedAndUnstaged():
    index_path = path.join(getGitParentPath(), '.lgit/index')
    idx_content = getFileContent(index_path)
    staged_files = []
    unstaged_files = []
    for line in idx_content:
        if isStagedFile(line):
            staged_files.append(getInfoOfField(line, 4))
        if isUnstagedFile(line):
            unstaged_files.append(getInfoOfField(line, 4))
    return staged_files, unstaged_files


def isCommitNoChange():
    index_path = path.join(getGitParentPath(), '.lgit/index')
    idx_content = getFileContent(index_path)
    nochange = True
    for line in idx_content:
        hash_field2 = getInfoOfField(line, 2)
        hash_field3 = getInfoOfField(line, 3)
        if hash_field2 != hash_field3:
            nochange = False
            break
    return nochange


def printStaged(staged_files):
    print("Changes to be committed:")
    print("  (use \"./lgit.py reset HEAD ...\" to unstage)")
    print()
    for file_path in staged_files:
        abspath = path.join(getGitParentPath(), file_path)
        rel_path = path.relpath(abspath)
        print('\tmodified:  %s' % rel_path)
    print()


def printUnstaged(unstaged_files):
    print("Changes not staged for commit:")
    print("  (use \"./lgit.py add ...\" to update what will be committed)")
    print("  (use \"./lgit.py checkout -- ...\" to discard changes\
 in working directory")
    print()
    for file_path in unstaged_files:
        abspath = path.join(getGitParentPath(), file_path)
        rel_path = path.relpath(abspath)
        print('\tmodified:  %s' % rel_path)
    print()


def printUntracked(untracked_files):
    print("Untracked files:")
    print("  (use \"./lgit.py add <file>...\" to include\
 in what will be committed)")
    print()
    for file_path in untracked_files:
        rel_path = path.relpath(file_path)
        print('\t' + rel_path)
    print()


def printHeader(git_path):
    print('On branch master\n')
    if listdir(path.join(git_path, '.lgit/commits')):
        print("Your branch is up-to-date with 'origin/master'.\n")
    else:
        print("No commits yet\n")


def printTailer(git_path):
    if not (listdir(path.join(git_path, '.lgit/commits')) and
            listdir(path.join(git_path, '.lgit/objects'))):
        print("nothing added to commit but untracked files present\
 (use \"./lgit.py add\" to track)")
    elif isCommitNoChange():
        print("no changes added to commit (use \"./lgit.py add and/or\
 \"./lgit.py commit -a\")")


def showStatus(git_path, staged_files, unstaged_files, untracked_files):
    printHeader(git_path)
    if staged_files:
        printStaged(staged_files)
    if unstaged_files:
        printUnstaged(unstaged_files)
    if untracked_files:
        printUntracked(untracked_files)
    printTailer(git_path)


def checkGitStt():
    git_path = getGitParentPath()
    # get all filename in git directory
    file_paths = getDirRecursively(git_path)
    tracked_files, untracked_files = getTrackAndUntrack(file_paths)

    if tracked_files:
        for file_path in tracked_files:
            updateIndex(file_path, 'status')

    staged_files, unstaged_files = getStagedAndUnstaged()
    showStatus(git_path, staged_files, unstaged_files, untracked_files)


'''_____________________GIT LS-FILES_________________________________'''


def getPathFromCurDir(path):
    cur_dir = getcwd()
    new_path = path[len(cur_dir)+1:]
    return new_path


def lsFileGit():
    # get all file path in current directory
    file_paths = getDirRecursively(getcwd())
    list_file = []
    # get new file path relative to current directory
    for path in file_paths:
        if isTrackedFile(path):
            new_path = getPathFromCurDir(path)
            list_file.append(new_path)
    # print the file list
    for path in sorted(list_file):
        print(path)


'''__________________GIT LOG_________________________________'''


# Get the sorted list of files in commits dir
def getCommitsFiles(lgit_path):
    commits_path = path.join(lgit_path, 'commits')
    paths = []
    for root, _, files in walk(commits_path):
        for file in files:
            file_path = path.join(root, file)
            paths.append(file_path)
    return sorted((paths), key=lambda x: float(x.split('/')[-1]), reverse=True)


def getReadableTime(file):
    ts = path.getmtime(file)
    return datetime.fromtimestamp(float(ts)).strftime('%a %b %d %H:%M:%S %Y')


def logGit(lgit_path):
    commit_paths = getCommitsFiles(lgit_path)
    if not commit_paths:
        print("fatal: your current branch 'master' does" +
              " not have any commits yet")
    else:
        for path in commit_paths:
            path_content = getFileContent(path)
            print('commit', path.split('/')[-1])
            print('Author:', path_content[0].strip('\n'))
            print('Date: {}\n'.format(getReadableTime(path)))
            print('\t{}\n'.format(path_content[3]))


'''_____________________GIT RM_________________________________'''


def rmIndex(file, lgit_path):
    index_path = path.join(lgit_path, 'index')
    index_file_path = getIndexFileName(path.abspath(file))
    index_content = getFileContent(index_path)
    idx_line_file = detectLineOfFile(index_file_path, index_content)
    if idx_line_file is not None:
        del index_content[idx_line_file]
        new_index_content = ''.join(index_content)
        writeFileContent(index_path, new_index_content)
        return True
    else:
        print("fatal: pathspec '{}' did not match any files".format(file))
        return False


def rmGit(file, lgit_path):
    file_path = path.abspath(file)
    if rmIndex(file, lgit_path):
        unlink(file_path)


'''_____________________GIT CONFIG_________________________________'''


def configGit(author, lgit_path):
    config_path = path.join(lgit_path, 'config')
    writeFileContent(config_path, author + '\n')
