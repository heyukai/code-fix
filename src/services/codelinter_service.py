import os
import subprocess
from typing import List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("mydemo.env")


class CodelinterService:
    """Codelinter 服务类，提供代码缺陷检测功能"""
    
    @staticmethod
    def parse_codelinter_text_output(text_output: str) -> List[Dict[str, Any]]:
        """
        解析 codelinter 文本输出，提取缺陷信息
        
        Args:
            text_output: codelinter 的原始文本输出
            
        Returns:
            缺陷列表，每个缺陷包含规则、类型、严重程度、描述、文件、行号、列号等信息
        """
        defects = []
        lines = text_output.strip().split('\n')
        current_file = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 跳过进度和状态信息
            if any(skip in line for skip in ['Working...', 'Finished...', 'Currently active', 'CodeLinter found', 'Defects:', 'The configuration file']):
                continue
                
            # 检查是否是文件路径行 (格式: /path/to/file.ets(数字) 或 F:\path\to\file.ets(数字))
            if line.endswith(')') and '(' in line and (line.startswith('/') or ':' in line):
                if '(' in line:
                    current_file = line.split('(')[0]
                continue
                
            # 解析缺陷行 (格式: 行号:列号 级别 描述 @规则名)
            if ':' in line and current_file:
                try:
                    line_parts = line.split(':', 1)
                    if len(line_parts) >= 2:
                        line_number_str = line_parts[0].strip()
                        rest_content = line_parts[1].strip()
                        
                        try:
                            line_number = int(line_number_str)
                        except ValueError:
                            continue
                            
                        content_parts = rest_content.split(None, 2)
                        if len(content_parts) >= 2:
                            try:
                                column_number = int(content_parts[0])
                                severity = content_parts[1]
                                content = content_parts[2] if len(content_parts) > 2 else ""
                            except ValueError:
                                column_number = 0
                                severity = content_parts[0] if content_parts else "unknown"
                                content = ' '.join(content_parts[1:]) if len(content_parts) > 1 else ""
                        else:
                            column_number = 0
                            severity = "unknown"
                            content = rest_content
                            
                        if content:
                            content_parts = content.split()
                            rule_name = "unknown"
                            description_parts = []
                            
                            for i, part in enumerate(content_parts):
                                if part.startswith('@'):
                                    rule_name = part[1:]
                                    description_parts = content_parts[:i]
                                    break
                                else:
                                    description_parts.append(part)
                                    
                            description = ' '.join(description_parts).strip()
                        else:
                            rule_name = "unknown"
                            description = ""
                            
                        # 严重程度映射
                        severity_map = {
                            'suggestion': 'low',
                            'warn': 'medium',
                            'error': 'high'
                        }
                        
                        # 规则类型判断
                        rule_type = "unknown"
                        if 'performance' in rule_name:
                            rule_type = "performance"
                        elif 'security' in rule_name:
                            rule_type = "security"
                        elif 'style' in rule_name:
                            rule_type = "style"
                            
                        defect = {
                            "rule": rule_name,
                            "type": rule_type,
                            "severity": severity_map.get(severity, severity),
                            "description": description,
                            "file": current_file,
                            "line": line_number,
                            "column": column_number,
                            "original_severity": severity
                        }
                        defects.append(defect)
                except Exception as e:
                    continue
                    
        return defects
    
    @staticmethod
    def run_codelinter_logic(code: str, language: str) -> List[Dict[str, Any]]:
        """
        执行 codelinter 核心逻辑
        
        Args:
            code: 要分析的代码
            language: 编程语言 (arkts 或其他)
            
        Returns:
            缺陷列表或错误信息
        """
        print(f"执行 codelinter 核心逻辑，语言: {language}...")
        
        ext = ".ets" if language == "arkts" else ".ts"
        code_dir = os.getenv("CODELINTER_CODE_DIR", "/app/src/A21_C__open-harmony/entry/")
        code_filename = "temp_code.ets"
        code_filepath = os.path.join(code_dir, code_filename)
        result_filepath = os.getenv("CODELINTER_RESULT_FILEPATH", "/app/src/A21_C__open-harmony/entry/result")
        
        process = None  # 初始化 process 变量
        try:
            # 创建目录并写入代码文件
            os.makedirs(code_dir, exist_ok=True)
            with open(code_filepath, "w", encoding="utf-8") as f:
                f.write(code)
                
            # 设置环境变量 - 使用 Docker 中安装的 Node.js
            env = os.environ.copy()
            env["DEVECO_NODE_HOME"] = "/usr/local/node"
            env["DEVECO_SDK_HOME"] = "/app/src/codelinter/command-line-tools/sdk"
            env["PATH"] = f"{env['DEVECO_NODE_HOME']}/bin:{env.get('PATH', '')}"
             
            # 执行 codelinter 命令
            command = ["codelinter", code_dir,"-o", result_filepath]
            print(f"执行命令: {' '.join(command)}")
            print(f"环境变量: DEVECO_NODE_HOME={env.get('DEVECO_NODE_HOME')}")
            print(f"环境变量: DEVECO_SDK_HOME={env.get('DEVECO_SDK_HOME')}")
            print(f"环境变量: PATH={env.get('PATH')}")
            timeout = int(os.getenv("CODELINTER_TIMEOUT", "300"))
            
            process = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True, 
                timeout=timeout
            )
            
            # 打印执行结果
            print(f"✅ codelinter 执行成功")
            print(f"📄 STDOUT: {process.stdout}")
            print(f"⚠️  STDERR: {process.stderr}")
            print(f"🔢 返回码: {process.returncode}")
            
            # 读取结果文件
            if os.path.exists(result_filepath):
                with open(result_filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
                    return CodelinterService.parse_codelinter_text_output(raw)
                    
            return []
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Codelinter 工具执行失败:")
            print(f"   命令: {' '.join(command)}")
            print(f"   返回码: {e.returncode}")
            print(f"   STDOUT: {e.stdout}")
            print(f"   STDERR: {e.stderr}")
            return [{"error": f"Codelinter 工具执行失败: {e.stderr}"}]
        except Exception as e:
            print(f"💥 未知错误:")
            print(f"   命令: {' '.join(command)}")
            print(f"   错误类型: {type(e).__name__}")
            print(f"   错误信息: {e}")
            import traceback
            print(f"   堆栈跟踪:")
            traceback.print_exc()
            return [{"error": f"执行 codelinter 过程中发生未知错误: {e}"}]
        finally:
            # 清理临时文件
            if os.path.exists(code_filepath):
                os.remove(code_filepath)
