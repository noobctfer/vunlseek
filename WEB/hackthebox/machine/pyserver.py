from flask import Flask, send_from_directory, abort,request


app = Flask(__name__)

# 设置路由来提供当前目录下的文件
@app.route('/')
def serve_file():
    # 获取文件路径
    print(request.args.get('data'))
    return '200';

# 运行应用
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=9999,debug=True)
