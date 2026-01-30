## 1. 通过安装宝塔
    # 1. 安装宝塔
        打开https://www.bt.cn/new/download.html，在下方在线安装
        note:安装完成后请记下bt面板网址账号密码
    # 2. 安装必要插件
        打开打开宝塔面板，左侧下方点击应用商店，安装Nginx, MySQL
## 2. 系统环境与应用用户准备
    登录服务器后，不要直接用 root 运行程序。
    # 1. 更新系统包
        sudo apt update && sudo apt upgrade -y  # 如果是 Ubuntu/Debian
        sudo yum update -y                   # 如果是 CentOS
    # 2. 创建应用运行专用用户 (sc-web)
        sudo useradd -m -s /bin/bash sc-web
    # 3. 创建持久化数据目录
        sudo mkdir -p /var/lib/Conventional-SC-Dataset/data/images
        sudo chown -R sc-web:sc-web /var/lib/Conventional-SC-Dataset
    # 4.为所有用户安装miniconda
## 3. 拉取代码与依赖安装
    # 1. 准备代码目录
        sudo mkdir -p /var/www/Conventional-SC-Dataset
        sudo chown sc-web:sc-web /var/www/Conventional-SC-Dataset

    # 2. 切换到应用用户并克隆代码
        sudo su - sc-web
        cd /var/www/Conventional-SC-Dataset
        git clone https://github.com/JLU-ICCMS-MaYuan/Conventional-SC-Dataset.git

    # 3. 创建 Python 虚拟环境
        conda create -n Conventional-SC-Dataset python=3.10.19 -y
        source venv/bin/activate

    # 4. 安装依赖
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install gunicorn uvicorn

## 4. 修改 Systemd 服务配置文件
    # 1. 生成随机key
        python3 -c "import os; print(os.urandom(32).hex())"
        或随便选择
    # 2. 生成邮箱配置
        打开163邮箱并获取授权码（或其他邮箱
        参考https://blog.csdn.net/kissradish/article/details/108447972
    # 1. 创建systemd任务(粘贴以下内容)
        sudo nano /etc/systemd/system/Conventional-SC-Dataset.service

        [Unit]
        Description=Gunicorn instance to serve Conventional-Conventional-SC-Dataset
        After=network.target

        [Service]
        User=root
        Group=root
        WorkingDirectory=/var/www/Conventional-SC-Dataset
        Environment="DATA_DIR=/var/lib/Conventional-SC-Dataset/data"
        Environment="JWT_SECRET_KEY=your_key_here"#（在这里粘贴你的key）
        Environment="PATH=/root/anaconda3/envs/Conventional-SC-Dataset/bin"
        Environment="SMTP_SERVER=smtp.163.com" #（默认163邮箱）
        Environment="SMTP_PORT=465"
        Environment="SMTP_USERNAME=your_email@example.com" #(在这里填写你的邮箱)
        Environment="SMTP_PASSWORD=your_password" #(163邮箱此处填写授权码)
        Environment="SMTP_SENDER_EMAIL=your_email@example.com" #(在这里填写你的邮箱)
        ExecStart=/root/anaconda3/envs/Conventional-SC-Dataset/bin/gunicorn \
            -w 4 \
            -k uvicorn.workers.UvicornWorker \
            backend.main:app \
            --bind 127.0.0.1:8000
        [Install]
        WantedBy=multi-user.target

    # 2. 重载并重启
        sudo systemctl daemon-reload
        sudo systemctl restart Conventional-SC-Dataset

## 5. 宝塔配置
    # 1. 反向代理
        打开宝塔面板，在左侧网站中添加反代，域名为本机域名，代理地址为http://127.0.0.1:8000
    # 2. 数据查看
        在数据库SQLite中选择/var/lib/Conventional-SC-Dataset/data/superconductor.db
    # 3. 自动备份
        在宝塔应用商店中安装云盘并配置
        打开计划任务选择备份目录/var/lib/sc-dataset/data至云盘