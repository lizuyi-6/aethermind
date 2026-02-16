#!/usr/bin/env python3
"""
修复流式输出无法结束的问题
"""

import re

# 读取agent.py
with open('/root/test_2/agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 备份
with open('/root/test_2/agent.py.bak3', 'w', encoding='utf-8') as f:
    f.write(content)

# 修复1: 在_continue_writing_stream的while循环开始处添加更严格的终止条件
old_while_start = '''        while continuation_count < max_continuations:
            # 【修复】强制终止条件：如果第十章已存在且有实质内容，立即停止
            if "第十章" in full_content:'''

new_while_start = '''        while continuation_count < max_continuations:
            # 【修复】硬性超时检测：如果续写总时间超过30分钟，强制终止
            if not hasattr(self, '_stream_start_time'):
                self._stream_start_time = time.time()
            elif time.time() - self._stream_start_time > 1800:  # 30分钟硬性超时
                print(f" [硬性超时] 续写总时间超过30分钟，强制终止", flush=True)
                yield "\n[硬性超时] 续写总时间超过30分钟，强制终止\n"
                break
            
            # 【修复】强制终止条件：如果第十章已存在且有实质内容，立即停止
            if "第十章" in full_content:'''

if old_while_start in content:
    content = content.replace(old_while_start, new_while_start)
    print('修复1: 添加硬性超时检测 - 成功')
else:
    print('修复1: 添加硬性超时检测 - 未找到匹配')

# 修复2: 改进流式循环中的超时检测，使用更短的超时时间
old_timeout_check = '''                # 超时检测函数
                def check_timeout():
                    while not timeout_occurred[0]:
                        time.sleep(3)  # 每3秒检查一次
                        current_time = time.time()
                        # 如果超过90秒没有收到数据，或者总时间超过1200秒（20分钟），则超时
                        if (current_time - last_chunk_time[0] > 90) or (current_time - start_time > 1200):
                            timeout_occurred[0] = True
                            break'''

new_timeout_check = '''                # 超时检测函数
                def check_timeout():
                    while not timeout_occurred[0]:
                        time.sleep(2)  # 每2秒检查一次（更频繁）
                        current_time = time.time()
                        # 【修复】缩短超时时间：60秒没有收到数据，或者总时间超过600秒（10分钟），则超时
                        if (current_time - last_chunk_time[0] > 60) or (current_time - start_time > 600):
                            timeout_occurred[0] = True
                            print(f" [超时检测] 超时触发: 无数据{current_time - last_chunk_time[0]:.0f}秒，总时间{current_time - start_time:.0f}秒", flush=True)
                            break'''

if old_timeout_check in content:
    content = content.replace(old_timeout_check, new_timeout_check)
    print('修复2: 改进超时检测 - 成功')
else:
    print('修复2: 改进超时检测 - 未找到匹配')

# 修复3: 在空内容检测后添加更强制的终止逻辑
old_empty_check = '''                else:
                    print(" [警告：未获取到内容]", end="", flush=True)
                    # 空内容计为一次失败
                    if not hasattr(self, "_empty_content_count"):
                        self._empty_content_count = 0
                    self._empty_content_count += 1
                    if self._empty_content_count >= 3:
                        yield "[错误] 连续3次未获取到内容，停止续写"
                        break
                    continue'''

new_empty_check = '''                else:
                    print(" [警告：未获取到内容]", end="", flush=True)
                    # 空内容计为一次失败
                    if not hasattr(self, "_empty_content_count"):
                        self._empty_content_count = 0
                    self._empty_content_count += 1
                    
                    # 【修复】连续2次空内容就停止，避免无限循环
                    if self._empty_content_count >= 2:
                        yield "\n[错误] 连续2次未获取到内容，停止续写\n"
                        print(f" [强制终止] 连续{self._empty_content_count}次空内容", flush=True)
                        break
                    
                    # 【修复】如果内容已经足够长（超过4万字），即使没有新内容也停止
                    if len(full_content) >= 40000:
                        yield "\n[信息] 内容已足够长，停止续写\n"
                        print(f" [强制终止] 内容已达{len(full_content)}字符", flush=True)
                        break
                    continue'''

if old_empty_check in content:
    content = content.replace(old_empty_check, new_empty_check)
    print('修复3: 改进空内容检测 - 成功')
else:
    print('修复3: 改进空内容检测 - 未找到匹配')

# 修复4: 在函数结束时重置状态
old_func_end = '''            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in locals() else 0
                print(f"\n[错误] 续写时出错 (耗时 {elapsed:.1f}秒): {str(e)}", flush=True)
                if continuation_count >= 3:
                    print("[错误] 连续多次出错，停止续写", flush=True)
                    break
                continue
    
    def _save_report'''

new_func_end = '''            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in locals() else 0
                print(f"\n[错误] 续写时出错 (耗时 {elapsed:.1f}秒): {str(e)}", flush=True)
                if continuation_count >= 3:
                    print("[错误] 连续多次出错，停止续写", flush=True)
                    break
                continue
        
        # 【修复】在函数结束时重置状态，确保下次调用正常
        self._empty_content_count = 0
        self._continuation_fail_count = 0
        if hasattr(self, '_stream_start_time'):
            delattr(self, '_stream_start_time')
        print(f"\n[续写完成] 最终内容长度: {len(full_content)}字符", flush=True)
    
    def _save_report'''

if old_func_end in content:
    content = content.replace(old_func_end, new_func_end)
    print('修复4: 添加状态重置 - 成功')
else:
    print('修复4: 添加状态重置 - 未找到匹配')

# 保存修复后的文件
with open('/root/test_2/agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n修复完成！')
