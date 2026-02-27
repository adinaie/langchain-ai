# LangChain 项目

这是一个使用 LangChain 和 LangChain-OpenAI 的基本 Python 项目。

## 关于 venv 目录

`venv` 是 Python 的虚拟环境目录，用于隔离项目依赖：

- 它会创建一个独立的 Python 环境，与系统全局 Python 环境分开
- 可以避免不同项目之间的依赖冲突
- 方便项目的移植和部署
- 当您删除项目时，只需删除整个项目目录即可，不会影响系统其他部分

## 安装

1. 创建并激活虚拟环境：

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. 升级 pip：

   ```powershell
   python -m pip install --upgrade pip
   ```

3. 安装依赖：
   ```powershell
   pip install -r requirements.txt
   ```

## 使用

运行主脚本：

```powershell
python main.py
```
