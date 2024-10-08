#!/bin/bash

set -e

# Load GitHub token from environment variable
GITHUB_TOKEN=${GITHUB_TOKEN}
if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "\033[31mGITHUB_TOKEN environment variable is not set.\033[0m"  # Red color for errors
  exit 1
fi

# Define color codes
GREEN='\033[32m'
YELLOW='\033[38;5;226m'
RED='\033[31m'
NC='\033[0m'  # No Color

# Function to check if a tag exists in the repository
tag_exists() {
  local repo=$1
  local tag=$2
  echo "Checking if tag $tag exists in repository $repo..."
  local tags=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo/git/refs/tags")
  if echo "$tags" | grep -q "refs/tags/$tag"; then
    return 0
  else
    return 1
  fi
}

# Function to update the image tag in the specified YAML file
update_image_tag_in_yaml() {
  local repo=$1
  local file_path=$2
  local tag=$3

  if [ -f "$file_path" ]; then
    if [ "$repo" == "airflow" ]; then
      # Update the tag in the Airflow values.yaml file
      sed -i "s|\(images:\s*airflow:\s*tag:\s*\).*|\1$tag|g" "$file_path"
    else
      # Update the tag in the standard Kubernetes deployment.yaml file
      sed -i "s|\(image: .*:\).*|\1$tag|g" "$file_path"
    fi
    return 0
  else
    echo -e "${RED}Error: The file structure is not as expected or file not found: $file_path${NC}"
    return 1
  fi
}

# Read YAML file
if [ ! -f repos.yaml ]; then
  echo -e "${RED}repos.yaml file not found.${NC}"
  exit 1
fi

repositories=$(yq e '.repositories' repos.yaml)

# Get the length of the repositories array
repo_length=$(echo "$repositories" | yq e 'length' -)

# Iterate over repositories
for index in $(seq 0 $(($repo_length - 1))); do
  enabled=$(echo "$repositories" | yq e ".[$index].enabled" -)
  
  if [ "$enabled" == "true" ]; then
    repo=$(echo "$repositories" | yq e ".[$index].name" -)
    release_notes=$(echo "$repositories" | yq e -o=json ".[$index].release_notes" - | jq -r '.[]' | sed 's/^/- /')
    tag=$(echo "$repositories" | yq e ".[$index].tag" -)
    deployment_path=$(echo "$repositories" | yq e ".[$index].deployment_path" -)

    echo -e "${YELLOW}=================================================================================${NC}"
    echo -e "${YELLOW}Processing repository: $repo${NC}"

    if tag_exists "$repo" "$tag"; then
      echo -e "${GREEN}Tag $tag already exists in $repo. Skipping...${NC}"
      continue
    fi

    # Clone the repository and checkout the xyz branch
    echo -e "${GREEN}Tag $tag does not exist in $repo repo. Proceeding...${NC}"
    git clone "https://$GITHUB_TOKEN:x-oauth-basic@github.com/$repo.git" "${repo##*/}"
    cd "${repo##*/}"
    echo "Cloned repository $repo and switched to directory ${repo##*/}"
    git fetch origin xyz:xyz
    git checkout xyz
    echo "Checked out xyz branch"

    # Create or update release_info.txt with the tag and release notes
    echo -e "TAG: $tag\n\nRELEASE NOTES:\n$release_notes" > release_info.txt
    echo "release_info.txt file generated successfully."
    echo "release_info.txt content:"
    cat release_info.txt

    # Update the specified YAML file with the new tag
    if [ -n "$deployment_path" ] && [ "$deployment_path" != "null" ]; then
      if update_image_tag_in_yaml "$repo" "$deployment_path" "$tag"; then
        echo -e "${GREEN}$deployment_path file updated successfully${NC}"
      else
        cd ..
        rm -rf "${repo##*/}"
        continue
      fi
    fi

    # Commit and push the changes if there are any
    if [ -n "$(git status --porcelain)" ]; then
      git config --global user.name "github-actions"
      git config --global user.email "github-actions@github.com"
      git add .
      commit_message="Add release notes and update $deployment_path with $tag tag for prod"
      if [ -z "$deployment_path" ] || [ "$deployment_path" == "null" ]; then
        commit_message="Add release notes for github release"
      fi
      git commit -m "$commit_message"
      echo "Committed changes to git"
      git push origin xyz
      echo -e "${GREEN}Pushed release changes to xyz branch.${NC}"
      echo -e "${YELLOW}To TAG and RELEASE '${repo##*/}' repository, merge 'xyz' into 'main' branch which will kick off its build and release pipeline.${NC}"
    else
      echo "No changes to commit. Intended Changes are already in '${repo##*/} - xyz' branch."
    fi

    if [ -n "$deployment_path" ] && [ "$deployment_path" != "null" ]; then
      echo "Updated $repo with new image tag for prod env and release notes"
    fi

    # Go back to the root directory
    cd ..
    rm -rf "${repo##*/}"
    echo -e "Cleaned up local repository ${repo}"
  fi
done