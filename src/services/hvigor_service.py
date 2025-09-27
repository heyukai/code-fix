import os
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HvigorService:
    """处理压缩包解压和hvigorw命令执行的服务"""
    
    def __init__(self):
        self.tmp_project_dir = Path("/app/tmpproject")
        self.tmp_project_dir.mkdir(parents=True, exist_ok=True)
    
    def find_zip_files(self) -> list:
        """
        在app/tmpproject目录中查找所有压缩包文件
        
        Returns:
            list: 找到的压缩包文件路径列表
        """
        zip_files = []
        for file_path in self.tmp_project_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.zip', '.rar', '.7z']:
                zip_files.append(str(file_path))
        
        logger.info(f"找到 {len(zip_files)} 个压缩包文件: {zip_files}")
        return zip_files
    
    def extract_zip(self, zip_path: str, extract_to: str = None) -> str:
        """
        解压zip文件
        
        Args:
            zip_path: 压缩包路径
            extract_to: 解压目标路径，如果为None则在同目录解压
            
        Returns:
            str: 解压后的目录路径
        """
        zip_path = Path(zip_path)
        
        if extract_to is None:
            extract_to = self.tmp_project_dir / zip_path.stem
        else:
            extract_to = Path(extract_to)
        
        extract_to.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            logger.info(f"成功解压 {zip_path} 到 {extract_to}")
            return str(extract_to)
        except Exception as e:
            logger.error(f"解压 {zip_path} 失败: {e}")
            raise
    
    def clean_directory_contents(self, directory: str) -> None:
        """
        清理指定目录下的所有文件和子目录，但保留该目录本身
        
        Args:
            directory: 需要清理的目录路径
        """
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            logger.info(f"目录不存在或不是目录，无需清理: {dir_path}")
            return
        for child in dir_path.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(child)
            except Exception as e:
                logger.warning(f"清理 {child} 时出错: {e}")
    
    def run_hvigorw_command(self, project_dir: str) -> dict:
        """
        在指定目录运行 hvigorw assembleHap -p buildMode=debug 命令
        
        Args:
            project_dir: 项目目录路径
            
        Returns:
            dict: 包含命令执行结果的字典
        """
        project_dir = Path(project_dir)
        
        if not project_dir.exists():
            raise FileNotFoundError(f"项目目录不存在: {project_dir}")
        
        cmd = ["hvigorw", "assembleHap", "-p", "buildMode=debug"]
        
        try:
            logger.info(f"在目录 {project_dir} 中执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd),
                "working_directory": str(project_dir)
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {' '.join(cmd)}")
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": "命令执行超时",
                "command": " ".join(cmd),
                "working_directory": str(project_dir)
            }
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "command": " ".join(cmd),
                "working_directory": str(project_dir)
            }
    
    def process_zip_and_run_hvigorw(self, zip_path: str = None) -> dict:
        """
        处理压缩包并运行hvigorw命令的完整流程
        
        Args:
            zip_path: 指定的压缩包路径，如果为None则自动查找
            
        Returns:
            dict: 处理结果
        """
        response: dict = {}
        extracted_dir: str | None = None
        try:
            if zip_path is None:
                zip_files = self.find_zip_files()
                if not zip_files:
                    response = {
                        "success": False,
                        "error": "在app/tmpproject目录中未找到压缩包文件",
                        "zip_files": [],
                        "extracted_dir": None,
                        "hvigorw_result": None
                    }
                    return response
                zip_path = zip_files[0]
                logger.info(f"自动选择压缩包: {zip_path}")
            
            extracted_dir = self.extract_zip(zip_path)
            hvigorw_result = self.run_hvigorw_command(extracted_dir)
            response = {
                "success": True,
                "zip_path": zip_path,
                "extracted_dir": extracted_dir,
                "hvigorw_result": hvigorw_result
            }
            return response
        except Exception as e:
            logger.error(f"处理流程失败: {e}")
            response = {
                "success": False,
                "error": str(e),
                "zip_path": zip_path,
                "extracted_dir": extracted_dir,
                "hvigorw_result": None
            }
            return response
        finally:
            # 运行完命令后清理 /app/tmpproject 目录下的所有文件（包括压缩包与解压后的目录）
            try:
                self.clean_directory_contents(str(self.tmp_project_dir))
                logger.info(f"已清理临时根目录内容: {self.tmp_project_dir}")
            except Exception as e:
                logger.warning(f"清理临时根目录内容失败 {self.tmp_project_dir}: {e}")
