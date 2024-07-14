#!/bin/bash

# Load GitHub token from environment variable
GITHUB_TOKEN=${GITHUB_TOKEN}
if [ -z "$GITHUB_TOKEN" ]; then
  echo "GITHUB_TOKEN environment variable is not set."
  exit 1
fi

# Function to create a git tag
create_git_tag() {
  local repo=$1
  local tag=$2

  # Get the latest commit SHA
  latest_commit_sha=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo/commits?per_page=1" | jq -r '.[0].sha')
  
  # Create a git tag
  create_tag_response=$(curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
    -d "{\"tag\": \"$tag\", \"message\": \"Tag $tag\", \"object\": \"$latest_commit_sha\", \"type\": \"commit\"}" \
    "https://api.github.com/repos/$repo/git/tags")

  tag_sha=$(echo "$create_tag_response" | jq -r '.sha')

  # Create the reference for the tag
  curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
    -d "{\"ref\": \"refs/tags/$tag\", \"sha\": \"$tag_sha\"}" \
    "https://api.github.com/repos/$repo/git/refs" > /dev/null

  echo "Tag $tag created for $repo"
}

# Function to create a release
create_release() {
  local repo=$1
  local tag=$2
  local release_notes=$3

  release_message=$(echo "$release_notes" | jq -Rs .)

  curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
    -d "{\"tag_name\": \"$tag\", \"name\": \"$tag\", \"body\": $release_message, \"draft\": false, \"prerelease\": false}" \
    "https://api.github.com/repos/$repo/releases" > /dev/null

  echo "Release $tag created for $repo"
}

# Read YAML file
repositories=$(yq e '.repositories' repos.yaml)

# Iterate over repositories
for index in $(seq 0 $(($(echo "$repositories" | yq e '. | length') - 1))); do
  enabled=$(echo "$repositories" | yq e ".[$index].enabled")
  
  if [ "$enabled" == "true" ]; then
    repo=$(echo "$repositories" | yq e ".[$index].name")
    release_notes=$(echo "$repositories" | yq e -o=json ".[$index].release_notes" | jq -r '.[]' | sed 's/^/- /')
    tag=$(echo "$repositories" | yq e ".[$index].tag")

    # Check if release with the specified tag already exists
    release_exists=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo/releases/tags/$tag" | jq -r '.message != "Not Found"')
    
    if [ "$release_exists" == "true" ]; then
      echo "Release with tag $tag already exists for $repo. Skipping..."
      continue
    fi

    # Create the git tag
    create_git_tag $repo $tag

    # Create the release with the specified tag
    create_release $repo $tag "$release_notes"
  fi
done