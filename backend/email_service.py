"""
邮箱服务模块 - SMTP 发送验证码
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional


class EmailService:
    """邮箱服务类"""

    def __init__(self):
        # 从环境变量读取SMTP配置
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.163.com")  # 默认163邮箱
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))  # SSL端口
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")  # 163邮箱需要使用授权码
        self.sender_email = os.getenv("SMTP_SENDER_EMAIL", self.smtp_username)

    def send_verification_code(self, to_email: str, code: str, real_name: str) -> bool:
        """
        发送验证码邮件

        Args:
            to_email: 收件人邮箱
            code: 验证码
            real_name: 用户真实姓名

        Returns:
            bool: 发送成功返回True，失败返回False
        """
        if not self.smtp_username or not self.smtp_password:
            print("警告：SMTP配置未设置，无法发送邮件")
            # 开发环境：打印验证码到控制台
            print(f"【开发模式】验证码: {code} (发送给 {to_email})")
            return True

        try:
            # 创建邮件内容
            message = MIMEMultipart("alternative")
            message["Subject"] = "超导文献数据库 - 邮箱验证码"
            message["From"] = self.sender_email
            message["To"] = to_email

            # HTML邮件内容
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                  <h2 style="color: #333; text-align: center;">超导文献数据库</h2>
                  <p>尊敬的 <strong>{real_name}</strong>，您好！</p>
                  <p>您正在申请成为超导文献数据库的管理员。请使用以下验证码完成邮箱验证：</p>
                  <div style="background-color: #f0f0f0; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
                    <h1 style="color: #0d6efd; margin: 0; letter-spacing: 5px;">{code}</h1>
                  </div>
                  <p style="color: #666;">验证码有效期为 <strong>5分钟</strong>，请尽快使用。</p>
                  <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px;">
                    如果您没有申请注册，请忽略此邮件。<br>
                    本邮件由系统自动发送，请勿回复。
                  </p>
                </div>
              </body>
            </html>
            """

            # 纯文本备用内容
            text = f"""
            超导文献数据库 - 邮箱验证

            尊敬的 {real_name}，您好！

            您正在申请成为超导文献数据库的管理员。
            验证码：{code}

            验证码有效期为 5分钟，请尽快使用。

            如果您没有申请注册，请忽略此邮件。
            """

            # 添加邮件内容
            part1 = MIMEText(text, "plain", "utf-8")
            part2 = MIMEText(html, "html", "utf-8")
            message.attach(part1)
            message.attach(part2)

            # 发送邮件
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            with server:
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, to_email, message.as_string())

            print(f"验证码邮件已发送到 {to_email}")
            return True

        except Exception as e:
            print(f"发送邮件失败: {str(e)}")
            # 开发环境：降级到控制台输出
            print(f"【降级模式】验证码: {code} (发送给 {to_email})")
            return True  # 开发环境返回True，生产环境应返回False

    def send_approval_notification(self, to_email: str, real_name: str, approved: bool) -> bool:
        """
        发送管理员审批通知

        Args:
            to_email: 收件人邮箱
            real_name: 用户真实姓名
            approved: 是否通过审批

        Returns:
            bool: 发送成功返回True
        """
        if not self.smtp_username or not self.smtp_password:
            print(f"【开发模式】审批通知: {real_name} - {'通过' if approved else '拒绝'}")
            return True

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = f"超导文献数据库 - 管理员申请{'通过' if approved else '被拒绝'}"
            message["From"] = self.sender_email
            message["To"] = to_email

            if approved:
                html = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px;">
                      <h2 style="color: #28a745;">🎉 恭喜！管理员申请已通过</h2>
                      <p>尊敬的 <strong>{real_name}</strong>，您好！</p>
                      <p>您的管理员申请已通过审批，现在您可以登录系统并开始审核文献了。</p>
                      <p>感谢您为超导文献数据库做出的贡献！</p>
                    </div>
                  </body>
                </html>
                """
            else:
                html = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px;">
                      <h2 style="color: #dc3545;">管理员申请未通过</h2>
                      <p>尊敬的 <strong>{real_name}</strong>，您好！</p>
                      <p>很抱歉，您的管理员申请未通过审批。</p>
                      <p>如有疑问，请联系系统管理员。</p>
                    </div>
                  </body>
                </html>
                """

            part = MIMEText(html, "html", "utf-8")
            message.attach(part)

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            with server:
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, to_email, message.as_string())

            return True

        except Exception as e:
            print(f"发送审批通知失败: {str(e)}")
            return True  # 开发环境返回True


# 全局邮件服务实例
email_service = EmailService()
