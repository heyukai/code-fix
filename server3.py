import asyncio
import uuid
import logging
from pathlib import Path
import aiofiles
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from src.services.rag_service import RAGService
from src.services.codelinter_service import CodelinterService
from src.services.hvigor_service import HvigorService
load_dotenv("mydemo.env")



mcp_server = FastMCP(name="CodelinterToolsServer", host="0.0.0.0", port=8000)

# --- 核心工具逻辑 ---
@mcp_server.tool()
async def run_codelinter_mcp_tool(code: str, language: str) -> list:
    """
    执行 codelinter 核心逻辑
    分析代码缺陷和错误信息
    Args:
        code: 要分析的代码
        language: 编程语言 (arkts 或其他)

    Returns:
        缺陷列表或错误信息
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, CodelinterService.run_codelinter_logic, code, language)

@mcp_server.tool()
async def search_similar_patterns(
    code: str,
    query: str = None,
    top_k: int = 5,
    include_metadata: bool = True,
    rule: str = None
) -> dict:
    """
    搜索相似的代码模式（RAG 向量检索）
    Args:
        code: 代码字符串
        query: 可选的查询字符串
        top_k: 返回的相似模式数量
        include_metadata: 是否包含元数据
        rule: 可选的规则过滤
    Returns:
        相似模式检索结果
    """
    rag_service = RAGService()
    await rag_service.initialize()
    result = await rag_service.search_similar_patterns(
        code=code,
        query=query,
        top_k=top_k,
        include_metadata=include_metadata,
        rule=rule
    )
    await rag_service.cleanup()
    return result

@mcp_server.tool()
async def extract_context_from_defects(
    code: str,
    defects: list = None,
    context_window: int = 5,
    include_similar_patterns: bool = False,
    auto_detect: bool = False,
    language: str = "arkts"
) -> dict:
    """
    基于缺陷检测结果提取上下文信息（仅支持单份代码分析）。
    如果 defects 为空，则自动调用 run_codelinter_mcp_tool 工具。
    """
    rag_service = RAGService()
    await rag_service.initialize()
    # 如果未传入 defects，自动检测
    if not defects:
        # 直接调用已注册的 codelinter 工具
        defects = await run_codelinter_mcp_tool(code, language)
    result = await rag_service.extract_context_from_defects(
        code=code,
        defects=defects,
        context_window=context_window,
        include_similar_patterns=include_similar_patterns,
        auto_detect=auto_detect
    )
    await rag_service.cleanup()
    return result

@mcp_server.tool()
async def process_zip_and_run_hvigorw(zip_path: str = None) -> dict:
    """
    对上传的harmony项目进行解压后编译，检查有没有语法错误、是否能够通过编译(目前仅支持上传一个项目压缩包后编译一个项目)
    在app/tmpproject目录中寻找压缩包文件，解压后运行hvigorw assembleHap -p buildMode=debug命令
    
    Args:
        zip_path: 指定的压缩包路径，如果为None则自动查找第一个压缩包
        
    Returns:
        dict: 包含处理结果的字典，包括解压路径和hvigorw命令执行结果
    """
    zip_path = None
    loop = asyncio.get_event_loop()
    hvigor_service = HvigorService()
    
    # 在executor中运行，避免阻塞事件循环
    result = await loop.run_in_executor(None, hvigor_service.process_zip_and_run_hvigorw, zip_path)
    
    return result

# --- 服务启动 ---
def run_mcp():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mcp_server.run(transport="sse")

if __name__ == "__main__":
    run_mcp()