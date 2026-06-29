"""直接启动入口

使用方式：
    cd backend
    python main.py

或带参数：
    python main.py --host 0.0.0.0 --port 8000
"""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="智能爬取系统后端服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="监听端口，默认 8000")
    parser.add_argument("--reload", action="store_true", default=True, help="是否开启热重载（默认开启）")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="关闭热重载")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
