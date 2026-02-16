# 服务器 pip 问题修复指南

## 🔴 错误信息

```
pkg_resources.VersionConflict: (pip 24.0, Requirement.parse('pip==20.0.2'))
DistributionNotFound: The 'pip==20.0.2' distribution was not found
```

## 📋 问题分析

服务器上的 pip 环境存在版本冲突：
- 当前 pip 版本：24.0
- 某个包要求：pip==20.0.2（旧版本）
- 这导致了版本冲突

## ✅ 解决方案

### 方案一：修复 pip 环境（推荐）

```bash
# 1. 重新安装 pip（使用 get-pip.py）
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py --force-reinstall

# 或者使用 pip 自己升级
python3 -m pip install --upgrade pip --force-reinstall

# 2. 清理 pip 缓存
pip3 cache purge

# 3. 重新安装依赖
pip3 install -r requirements.txt
```

### 方案二：使用 python3 -m pip（绕过 pip3 命令）

```bash
# 直接使用 Python 模块方式安装
python3 -m pip install -r requirements.txt

# 如果还有问题，先升级 pip
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### 方案三：修复 pkg_resources

```bash
# 重新安装 setuptools 和 pkg_resources
python3 -m pip install --upgrade setuptools wheel
python3 -m pip install --upgrade pip

# 然后安装依赖
python3 -m pip install -r requirements.txt
```

### 方案四：使用虚拟环境（最佳实践）

```bash
# 1. 安装 virtualenv（如果还没有）
python3 -m pip install virtualenv

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 升级 pip
pip install --upgrade pip

# 5. 安装依赖
pip install -r requirements.txt
```

## 🚀 快速修复命令（一键执行）

```bash
# 在服务器上执行以下命令
python3 -m pip install --upgrade pip setuptools wheel --force-reinstall && \
python3 -m pip cache purge && \
python3 -m pip install -r requirements.txt
```

## 📝 分步执行（如果一键命令失败）

### 步骤 1：修复 pip

```bash
python3 -m pip install --upgrade pip --force-reinstall
```

### 步骤 2：升级工具包

```bash
python3 -m pip install --upgrade setuptools wheel
```

### 步骤 3：清理缓存

```bash
python3 -m pip cache purge
```

### 步骤 4：安装依赖

```bash
python3 -m pip install -r requirements.txt
```

## 🔧 如果仍然失败

### 检查 Python 和 pip 版本

```bash
# 检查 Python 版本
python3 --version

# 检查 pip 版本
python3 -m pip --version

# 检查 pip3 命令
which pip3
pip3 --version
```

### 使用完整路径

```bash
# 如果 pip3 命令有问题，使用完整路径
/usr/local/bin/pip3 install -r requirements.txt

# 或者
/usr/bin/pip3 install -r requirements.txt
```

### 手动安装每个包

如果批量安装失败，可以逐个安装：

```bash
python3 -m pip install openai>=1.12.0
python3 -m pip install python-dotenv>=1.0.0
python3 -m pip install PyPDF2>=3.0.0
python3 -m pip install python-docx>=1.0.0
python3 -m pip install pandas>=2.0.0
python3 -m pip install openpyxl>=3.1.0
python3 -m pip install flask>=3.0.0
python3 -m pip install flask-cors>=4.0.0
```

## ⚠️ 注意事项

1. **不要降级 pip**：当前 pip 24.0 是较新版本，不应该降级到 20.0.2
2. **使用虚拟环境**：推荐使用虚拟环境，避免系统 Python 环境污染
3. **检查权限**：确保有足够的权限安装包（可能需要 sudo）

## 🎯 推荐方案

**最佳实践：使用虚拟环境**

```bash
# 创建虚拟环境
cd /var/www/html
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 运行 Flask 应用时，确保激活虚拟环境
source venv/bin/activate
python3 app.py
```

## 📞 如果问题持续

如果以上方法都不行，请提供：
1. `python3 --version` 的输出
2. `python3 -m pip --version` 的输出
3. `which python3` 的输出
4. 完整的错误信息

---

**最后更新**：2024-12-15

