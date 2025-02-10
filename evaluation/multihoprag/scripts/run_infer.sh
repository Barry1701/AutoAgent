current_dir=$(dirname "$(readlink -f "$0")")

cd $current_dir
cd ../
export DOCKER_WORKPLACE_NAME=workplace_rag
export EVAL_MODE=True
export DEBUG=True
export BASE_IMAGES=tjbtech1/gaia-bookworm:v2
export COMPLETION_MODEL=claude-3-5-sonnet-20241022


# export OPENAI_API_KEY=
# model=gpt-4o-2024-08-06
model=gpt-4o-mini-2024-07-18


# export MISTRAL_API_KEY=\
# model=mistral/mistral-large-2407

# export DEEPSEEK_API_KEY=
# model=deepseek/deepseek-chat
# model=deepseek/deepseek-coder

python AAAtestRAG_exp_json.py --model $model
# python AAAtestRAG_exp.py


python evaluation/gaia/run_infer.py --container_name gaia_lite_eval --model ${COMPLETION_MODEL} --test_pull_name test_pull_1225 --debug --eval_num_workers 1 --port 12345 --data_split validation --level 2023_all --agent_func get_system_triage_agent --git_clone
# python /Users/tangjiabin/Documents/reasoning/metachain/test_gaia_tool.py