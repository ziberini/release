from github import Github
from github import Auth
from datetime import datetime, timedelta
import base64


def naiveDecrypt(encrypted):
    # Decode the base64 encoded token and strip any newline characters
    decrypted_bytes = base64.b64decode(encrypted)
    return decrypted_bytes.decode('utf-8').strip()


def getLastCommitURL():
    encrypted = 'Z2hwX2FiUWFjckNMeDlPUFhIQm9pTDZzTFpkMDQ5YUVYZDRaMXIwYQo='
    token = naiveDecrypt(encrypted)
    auth = Auth.Token(token)
    g = Github(auth=auth)

    # Access the repository directly (replace 'your-username' with your actual GitHub username)
    repo = g.get_user('ziberini').get_repo('practice')

    # Limit to commits in past 24 hours
    since = datetime.now() - timedelta(days=1)
    commits = repo.get_commits(since=since)

    if commits.totalCount > 0:
        last = commits[0]
        return last.html_url
    else:
        return "No commits in the past 24 hours"


# Call the function
print(getLastCommitURL())


######
# HELLO HELLO
#####
