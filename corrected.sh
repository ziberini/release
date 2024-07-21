#!/bin/bash

# Load GitHub token from environment variable
GITHUB_TOKEN=${GITHUB_TOKEN}
if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "\033[31mGITHUB_TOKEN environment variable is not set.\033[0m"  # Red color for errors
  exit 1
fi

# Define color codes
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m'  # No Color

# Function to check if a repository exists
check_repo_exists() {
  local repo=$1
  repo_response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo")
  if [ "$repo_response" -ne 200 ]; then
    echo -e "${RED}Repository $repo does not exist. Skipping...${NC}"
    return 1
  fi
  return 0
}

# Function to create a git tag
create_git_tag() {
  local repo=$1
  local tag=$2

  # Get the latest commit SHA
  latest_commit_sha=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo/commits?per_page=1" | jq -r '.[0].sha')
  if [ -z "$latest_commit_sha" ]; then
    echo -e "${RED}Failed to get the latest commit SHA for repo $repo. Skipping...${NC}"
    return 1
  fi
  
  # Create a git tag
  create_tag_response=$(curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
    -d "{\"tag\": \"$tag\", \"message\": \"Tag $tag\", \"object\": \"$latest_commit_sha\", \"type\": \"commit\"}" \
    "https://api.github.com/repos/$repo/git/tags")
  
  tag_sha=$(echo "$create_tag_response" | jq -r '.sha')
  if [ -z "$tag_sha" ]; then
    echo -e "${RED}Failed to create tag $tag for repo $repo. Skipping...${NC}"
    return 1
  fi

  # Create the reference for the tag
  create_ref_response=$(curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
    -d "{\"ref\": \"refs/tags/$tag\", \"sha\": \"$tag_sha\"}" \
    "https://api.github.com/repos/$repo/git/refs")
  
  if echo "$create_ref_response" | jq -e '.ref' > /dev/null; then
    echo -e "${YELLOW}Tag $tag created for $repo${NC}"
  else
    echo -e "${RED}Failed to create the reference for tag $tag for repo $repo. Skipping...${NC}"
    return 1
  fi
}

# Function to create a release
create_release() {
  local repo=$1
  local tag=$2
  local release_notes=$3

  release_message=$(echo "$release_notes" | jq -Rs .)

  create_release_response=$(curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Content-Type: application/json" \
    -d "{\"tag_name\": \"$tag\", \"name\": \"$tag\", \"body\": $release_message, \"draft\": false, \"prerelease\": false}" \
    "https://api.github.com/repos/$repo/releases")
  
  if echo "$create_release_response" | jq -e '.id' > /dev/null; then
    echo -e "${YELLOW}Release $tag created for $repo${NC}"
  else
    echo -e "${RED}Failed to create release $tag for repo $repo. Skipping...${NC}"
  fi
}

# Read YAML file and convert to JSON
repositories=$(yq e -o=json '.repositories' repos.yaml)

# Iterate over repositories
length=$(echo "$repositories" | jq '. | length')
for index in $(seq 0 $(($length - 1))); do
  enabled=$(echo "$repositories" | jq -r ".[$index].enabled")
  
  if [ "$enabled" == "true" ]; then
    repo=$(echo "$repositories" | jq -r ".[$index].name")
    release_notes=$(echo "$repositories" | jq -r ".[$index].release_notes | .[] | \"- \(. | @text)\"" | tr '\n' '\n')
    tag=$(echo "$repositories" | jq -r ".[$index].tag")

    # Check if the repository exists
    if ! check_repo_exists "$repo"; then
      continue
    fi

    # Check if release with the specified tag already exists
    release_response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo/releases/tags/$tag")
    release_exists=$(echo "$release_response" | jq -r '.message != "Not Found"')
    
    if [ "$release_exists" == "true" ]; then
      echo -e "${GREEN}Release with tag $tag already exists for $repo. Skipping...${NC}"
      continue
    elif echo "$release_response" | jq -e '.message == "Not Found"' > /dev/null; then
      # Proceed if release does not exist
      :
    else
      echo -e "${RED}Error checking for release existence: $(echo "$release_response" | jq -r '.message'). Skipping...${NC}"
      continue
    fi

    # Create the git tag
    if ! create_git_tag $repo $tag; then
      continue
    fi

    # Create the release with the specified tag
    create_release $repo $tag "$release_notes"
  fi
done