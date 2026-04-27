from dotenv import find_dotenv, load_dotenv

# 在导入 backend 子模块前加载环境变量，确保 .env 对 API 配置生效
load_dotenv(find_dotenv())
