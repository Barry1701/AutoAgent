

from autoagent.environment.docker_env import DockerEnv, DockerConfig, check_container_ports, check_container_exist, check_container_running
from autoagent.tools.files import create_file

if __name__ == "__main__":
    import os
    os.environ["BASE_IMAGES"] = "tjbtech1/gaia-bookworm:amd64"
    config = DockerConfig(container_name = "gaia_amd64_test", 
    workplace_name = "workplace_gaia_amd64_test",
    communication_port = 12345,
    conda_path = "/root/miniconda3"
    )
    env = DockerEnv(config)
    env.init_container()
    res =  create_file(path = 'test.py', content = 'print("hello world")', env = env)
    print(res)