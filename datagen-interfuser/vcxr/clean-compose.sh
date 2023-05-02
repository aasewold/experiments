#!/bin/bash

compose_projects=$(docker compose ls -a | grep 'interfuser-datagen' | cut -d' ' -f1)

echo "This will stop and remove these compose projects:"
for project in $compose_projects; do
  echo "  $project"
done

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit 1
fi

for project in $compose_projects; do
  docker compose -p $project down
done
