# Red Trade

这是一个基于EMA和ATR指标的自动化交易策略项目，使用OKX交易所进行期货交易。策略结合时间周期判断顺势或逆势交易，并使用止损止盈机制。

## 安装

### 1. 创建虚拟环境

使用conda创建虚拟环境：

```bash
conda create -n red_trade python=3.12 -y
conda activate red_trade
```

### 2. 安装依赖

首先，确保已激活虚拟环境，然后安装Python包：

```bash
pip install -r requirements.txt
```

**注意：** TA-Lib 是技术分析库，可能需要系统级依赖。在macOS上，可以使用Homebrew安装：

```bash
brew install ta-lib
pip install TA-Lib
```

在其他系统上，请参考 [TA-Lib 官方文档](https://github.com/mrjbq7/ta-lib) 进行安装。

### 3. 配置环境变量

项目使用 `.env` 文件存储敏感信息（如API密钥、邮箱配置）。请创建并编辑 `.env` 文件：

```bash
cp .env.example .env  # 如果有示例文件，否则手动创建
```

在 `.env` 文件中填写以下信息：

```
OKX_API_KEY=your_api_key
OKX_API_SECRET=your_api_secret
OKX_API_PASSPHRASE=your_passphrase

EMAIL_TO=your_email@example.com
EMAIL_FROM=your_sender@example.com
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
```

**安全提醒：** 不要将 `.env` 文件提交到版本控制系统。

### 4. 运行程序

激活虚拟环境后，运行主程序：

```bash
python rt/real_try_okx.py
```

程序将持续监控市场并根据策略执行交易。使用 Ctrl+C 停止程序。

## 项目结构

- `rt/mark.py`: 策略信号生成模块
- `rt/utils.py`: 工具函数，包括数据获取和邮件通知
- `rt/real_try_okx.py`: 主程序，包含交易逻辑
- `rt/logs/`: 日志文件目录
- `.env`: 环境变量配置文件（请勿提交）

## 策略说明

- 使用EMA (指数移动平均线) 和 ATR (平均真实波幅) 计算上下轨
- 根据当前UTC时间判断顺势或逆势交易
- 实现止损和移动止盈机制
- 支持邮件通知交易信号

## 注意事项

- 这是一个高风险的自动化交易程序，请在测试环境中充分验证
- 确保API权限正确设置
- 监控账户余额和交易记录
- 建议从小额资金开始测试

## 许可证

[请添加许可证信息]</content>
<filePath>/Users/david/Documents/co-work/red_trade/README.md