import re

from git import GitCommandError, InvalidGitRepositoryError, Repo, TagObject

from .errors import GitError
from .settings import config

try:
    repo = Repo('.', search_parent_directories=True)
except InvalidGitRepositoryError:
    repo = None


def check_repo():
    if not repo:
        raise GitError("Not in a valid git repository")


def get_commit_log(from_rev=None):
    """
    Yields all commit messages from last to first.
    """

    check_repo()
    rev = None
    if from_rev:
        rev = '...{from_rev}'.format(from_rev=from_rev)
    for commit in repo.iter_commits(rev):
        yield (commit.hexsha, commit.message)


def get_last_version(skip_tags=None):
    """
    Return last version from repo tags.

    :return: A string contains version number.
    """

    check_repo()
    skip_tags = skip_tags or []

    def version_finder(tag):
        if isinstance(tag.commit, TagObject):
            return tag.tag.tagged_date
        return tag.commit.committed_date

    for i in sorted(repo.tags, reverse=True, key=version_finder):
        if re.match(r'v\d+\.\d+\.\d+', i.name):
            if i.name in skip_tags:
                continue
            return i.name[1:]


def get_version_from_tag(tag_name):
    """
    Gets commit hexsha for given ref tag.

    :param tag_name: The name of the sought rference tag.
    """

    check_repo()
    for i in repo.tags:
        if i.name == tag_name:
            return i.commit.hexsha


def get_repository_owner_and_name():
    """
    Checks the origin remote to get the owner and name of the remote repository.

    :return: A tuple of the owner and name.
    """

    check_repo()
    url = repo.remote('origin').url
    parts = re.search(r'([^/:]+)/([^/]+).git$', url)

    return parts.group(1), parts.group(2)


def get_current_head_hash():
    """
    Gets the commit hash of the current HEAD.

    :return: A string with the commit hash.
    """

    check_repo()
    return repo.head.commit.name_rev.split(' ')[0]


def commit_new_version(version):
    """
    Commits the file containing the version number variable with the version number as the commit
    message.

    :param version: The version number to be used in the commit message.
    """

    check_repo()
    repo.git.add(config.get('semantic_release', 'version_variable').split(':')[0])
    return repo.git.commit(m=version, author="semantic-release <semantic-release>")


def tag_new_version(version):
    """
    Creates a new tag with the version number prefixed with v.

    :param version: The version number used in the tag as a string.
    """

    check_repo()
    return repo.git.tag('-a', 'v{0}'.format(version), m='v{0}'.format(version))


def push_new_version(gh_token=None, owner=None, name=None):
    """
    Runs git push and git push --tags.

    :param gh_token: Github token used to push.
    :param owner: Organisation or user that owns the repository.
    :param name: Name of repository.
    """

    check_repo()
    server = 'origin'
    if gh_token:
        server = 'https://{token}@{repo}'.format(
            token=gh_token,
            repo='github.com/{owner}/{name}.git'.format(owner=owner, name=name)
        )

    try:
        repo.git.push(server, 'master')
        repo.git.push('--tags', server, 'master')
    except GitCommandError as error:
        message = str(error)
        if gh_token:
            message = message.replace(gh_token, '[GH_TOKEN]')
        raise GitError(message)


def checkout(branch):
    """
    Checks out the given branch in the local repository.

    :param branch: The branch to checkout.
    """

    check_repo()
    return repo.git.checkout(branch)
