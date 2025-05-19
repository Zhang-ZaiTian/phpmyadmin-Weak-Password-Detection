# phpmyadmin 弱口令探测


多线程phpMyAdmin登录爆破脚本，适用于CTF及授权渗透测试场景

## 功能特性
- 多线程并发请求（默认20线程）
- 自动处理登录Token验证
- 实时尝试计数器
- 终端彩色状态输出
- 成功结果自动记录至`success.txt`
- 支持用户中断操作

## 配置要求
- Python 3.6+
- requests库 (`pip install requests`)

## 使用说明
1. 修改脚本头部参数：
```python
target = 'http://target_url/phpmyadmin/'  # 目标地址
user = 'root'                            # 目标账户
passdic = 'path/to/password_list.txt'     # 密码字典路径
```

2. 执行脚本：
```bash
python phpmyadmin密码爆破.py
```

3. 观察输出：
- 成功密码显示为绿色
- 错误信息显示为黄色
- 最终结果保存至当前目录的success.txt

## 注意事项
- 密码字典建议使用Top 100/500等常用弱口令集合
- 线程数根据网络环境调整
- 仅限合法授权测试场景使用
- 使用者需自行承担相关法律责任

> 该工具禁止用于未授权测试，开发者不承担任何滥用造成的后果
