import re

with open("/root/test_2/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# 备份
with open("/root/test_2/agent.py.bak6", "w", encoding="utf-8") as f:
    f.write(content)

# 修复1: 添加硬性超时 - 使用反斜杠n字符串
old1 = """        while continuation_count < max_continuations:
            # 【修复】强制终止条件：如果第十章已存在且有实质内容，立即停止
            if "第十章" in full_content:"""

new1 = """        while continuation_count < max_continuations:
            # 【修复】硬性超时检测
            if not hasattr(self, "_stream_start_time"):
                self._stream_start_time = time.time()
            elif time.time() - self._stream_start_time > 1800:
                print(f" [硬性超时] 续写总时间超过30分钟", flush=True)
                yield "\n[硬性超时] 强制终止\n"
                break
            
            # 【修复】强制终止条件：如果第十章已存在且有实质内容，立即停止
            if "第十章" in full_content:"""

if old1 in content:
    content = content.replace(old1, new1)
    print("修复1成功")
else:
    print("修复1未匹配")

# 修复2: 改进超时检测
old2 = """                # 超时检测函数
                def check_timeout():
                    while not timeout_occurred[0]:
                        time.sleep(3)  # 每3秒检查一次
                        current_time = time.time()
                        # 如果超过90秒没有收到数据，或者总时间超过1200秒（20分钟），则超时
                        if (current_time - last_chunk_time[0] > 90) or (current_time - start_time > 1200):
                            timeout_occurred[0] = True
                            break"""

new2 = """                # 超时检测函数
                def check_timeout():
                    while not timeout_occurred[0]:
                        time.sleep(2)
                        current_time = time.time()
                        # 缩短超时：60秒无数据或总时间600秒
                        if (current_time - last_chunk_time[0] > 60) or (current_time - start_time > 600):
                            timeout_occurred[0] = True
                            print(f" [超时触发]", flush=True)
                            break"""

if old2 in content:
    content = content.replace(old2, new2)
    print("修复2成功")
else:
    print("修复2未匹配")

# 修复3: 改进空内容检测
old3 = """                else:
                    print(" [警告：未获取到内容]", end="", flush=True)
                    # 空内容计为一次失败
                    if not hasattr(self, "_empty_content_count"):
                        self._empty_content_count = 0
                    self._empty_content_count += 1
                    if self._empty_content_count >= 3:
                        yield "[错误] 连续3次未获取到内容，停止续写"
                        break
                    continue"""

new3 = """                else:
                    print(" [警告：未获取到内容]", end="", flush=True)
                    if not hasattr(self, "_empty_content_count"):
                        self._empty_content_count = 0
                    self._empty_content_count += 1
                    if self._empty_content_count >= 2:
                        yield "\n[错误] 连续2次未获取内容，停止\n"
                        break
                    if len(full_content) >= 40000:
                        yield "\n[信息] 内容足够，停止\n"
                        break
                    continue"""

if old3 in content:
    content = content.replace(old3, new3)
    print("修复3成功")
else:
    print("修复3未匹配")

with open("/root/test_2/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("修复完成")
