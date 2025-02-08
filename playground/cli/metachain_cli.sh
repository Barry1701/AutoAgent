current_dir=$(dirname "$(readlink -f "$0")")

cd $current_dir
cd ../..
export DOCKER_WORKPLACE_NAME=workplace
export EVAL_MODE=True
export DEBUG=True
export BASE_IMAGES=tjbtech1/gaia-bookworm:v2
export COMPLETION_MODEL=claude-3-5-sonnet-20241022
# export COMPLETION_MODEL=gpt-4o-2024-08-06
export DEBUG=True
export MC_MODE=True
export AI_USER=tjb-tech

python playground/cli/metachain_cli.py --container_name quick_start --model ${COMPLETION_MODEL} --test_pull_name mirror_branch_0207 --debug --port 12345 --git_clone
