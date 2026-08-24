package services

import (
	"crypto/tls"
	"fmt"
	"net"
	"net/smtp"
	"strings"
	"time"
)

type EmailConfig struct {
	Host, Port, Username, Password, From, TLSMode string
}

type Mailer interface {
	SendVerificationCode(to, code string) error
}

type SMTPMailer struct {
	config EmailConfig
}

func NewSMTPMailer(config EmailConfig) *SMTPMailer { return &SMTPMailer{config: config} }

func (m *SMTPMailer) Configured() bool {
	return m.config.Host != "" && m.config.From != ""
}

func (m *SMTPMailer) SendVerificationCode(to, code string) error {
	if !m.Configured() {
		return fmt.Errorf("SMTP 未配置")
	}
	addr := net.JoinHostPort(m.config.Host, m.config.Port)
	subject := "SC-Wiki 邮箱验证码"
	body := fmt.Sprintf("您的 SC-Wiki 验证码是：%s\r\n验证码 5 分钟内有效，请勿转发。", code)
	message := []byte("From: " + m.config.From + "\r\nTo: " + to + "\r\nSubject: " + subject + "\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n" + body)
	var auth smtp.Auth
	if m.config.Username != "" {
		auth = smtp.PlainAuth("", m.config.Username, m.config.Password, m.config.Host)
	}
	if strings.EqualFold(m.config.TLSMode, "implicit") {
		conn, err := tls.DialWithDialer(&net.Dialer{Timeout: 10 * time.Second}, "tcp", addr, &tls.Config{ServerName: m.config.Host, MinVersion: tls.VersionTLS12})
		if err != nil {
			return err
		}
		defer conn.Close()
		client, err := smtp.NewClient(conn, m.config.Host)
		if err != nil {
			return err
		}
		defer client.Close()
		if auth != nil {
			if err := client.Auth(auth); err != nil {
				return err
			}
		}
		if err := client.Mail(m.config.From); err != nil {
			return err
		}
		if err := client.Rcpt(to); err != nil {
			return err
		}
		writer, err := client.Data()
		if err != nil {
			return err
		}
		if _, err = writer.Write(message); err != nil {
			return err
		}
		if err = writer.Close(); err != nil {
			return err
		}
		return client.Quit()
	}
	return smtp.SendMail(addr, auth, m.config.From, []string{to}, message)
}
