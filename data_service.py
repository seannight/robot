"""
泰迪杯智能客服系统 - 数据服务模块
负责文档处理和数据提取
"""
import os
import logging
import re
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

class DataService:
    """数据服务：负责处理各种格式的文档和数据提取"""
    
    def __init__(self, storage_path: str = "data/processed"):
        """
        初始化数据服务
        
        Args:
            storage_path: 处理后数据存储路径
        """
        self.storage_path = Path(storage_path)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"数据服务初始化，存储路径: {self.storage_path}")
        
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        
        # 尝试导入PDF处理库
        try:
            import fitz  # PyMuPDF
            self.pdf_support = True
        except ImportError:
            self.logger.warning("未安装PyMuPDF库，PDF处理功能将受限")
            self.pdf_support = False
            
        # 尝试导入图像处理库
        try:
            import cv2
            import pytesseract
            self.ocr_support = True
        except ImportError:
            self.logger.warning("未安装OpenCV或pytesseract库，OCR功能将不可用")
            self.ocr_support = False
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        处理PDF文件，提取文本和元数据
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            包含PDF内容的字典
        """
        if not os.path.exists(pdf_path):
            self.logger.error(f"PDF文件不存在: {pdf_path}")
            return {"error": "文件不存在"}
            
        if not self.pdf_support:
            self.logger.error("缺少PDF处理支持")
            return {"error": "缺少PDF处理支持，请安装PyMuPDF库"}
            
        try:
            import fitz  # PyMuPDF
            
            # 打开PDF文件
            doc = fitz.open(pdf_path)
            
            # 提取基本信息
            info = {
                "filename": os.path.basename(pdf_path),
                "path": pdf_path,
                "page_count": len(doc),
                "title": doc.metadata.get("title", os.path.basename(pdf_path)),
                "author": doc.metadata.get("author", "未知"),
                "creation_date": doc.metadata.get("creationDate", "未知"),
                "pages": []
            }
            
            # 逐页提取文本
            for page_num, page in enumerate(doc):
                page_info = {
                    "page_num": page_num + 1,
                    "text": page.get_text(),
                    "images": []
                }
                
                # 提取图像信息（不保存图像数据，只记录元数据）
                for img_index, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image:
                        img_info = {
                            "index": img_index,
                            "width": base_image["width"],
                            "height": base_image["height"]
                        }
                        page_info["images"].append(img_info)
                
                info["pages"].append(page_info)
            
            # 保存处理结果
            output_path = self.storage_path / f"{os.path.splitext(os.path.basename(pdf_path))[0]}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"PDF处理完成: {pdf_path}")
            return info
            
        except Exception as e:
            self.logger.error(f"处理PDF时出错: {e}")
            return {"error": str(e)}
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        使用OCR从图像中提取文本
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            提取的文本
        """
        if not os.path.exists(image_path):
            self.logger.error(f"图像文件不存在: {image_path}")
            return ""
            
        if not self.ocr_support:
            self.logger.error("缺少OCR支持")
            return ""
            
        try:
            import cv2
            import pytesseract
            
            # 读取图像
            img = cv2.imread(image_path)
            
            # 图像预处理
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 自适应阈值处理，提高OCR准确率
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # 使用pytesseract进行OCR
            text = pytesseract.image_to_string(thresh, lang='chi_sim+eng')
            
            self.logger.info(f"图像OCR处理完成: {image_path}")
            return text
            
        except Exception as e:
            self.logger.error(f"OCR处理时出错: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """
        清理和规范化文本
        
        Args:
            text: 输入文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
            
        # 删除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 删除特殊字符但保留中文标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff。，？！：；""''【】（）、]', '', text)
        
        return text.strip()
    
    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取结构化数据
        
        Args:
            text: 输入文本
            
        Returns:
            结构化数据
        """
        data = {
            "dates": [],
            "emails": [],
            "urls": [],
            "numbers": []
        }
        
        # 提取日期 (支持多种格式)
        date_patterns = [
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?',  # YYYY-MM-DD
            r'\d{1,2}[-/月]\d{1,2}[日]?[-/]\d{4}[年]?'  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            data["dates"].extend(matches)
        
        # 提取电子邮件
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        data["emails"] = re.findall(email_pattern, text)
        
        # 提取URL
        url_pattern = r'https?://\S+'
        data["urls"] = re.findall(url_pattern, text)
        
        # 提取数字
        number_pattern = r'\d+\.?\d*'
        data["numbers"] = re.findall(number_pattern, text)
        
        return data
    
    def create_text_files(self, pdf_path: str, output_dir: str = "data/knowledge/txt") -> List[str]:
        """
        从PDF创建纯文本文件，方便索引
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            
        Returns:
            创建的文本文件路径列表
        """
        if not os.path.exists(pdf_path):
            self.logger.error(f"PDF文件不存在: {pdf_path}")
            return []
            
        if not self.pdf_support:
            self.logger.error("缺少PDF处理支持")
            return []
            
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 处理PDF
            pdf_info = self.process_pdf(pdf_path)
            if "error" in pdf_info:
                return []
                
            file_paths = []
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            
            # 整份文档的文本
            full_text = ""
            for page in pdf_info["pages"]:
                full_text += page["text"] + "\n\n"
                
            # 保存整份文档
            full_path = os.path.join(output_dir, f"{base_name}_full.txt")
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            file_paths.append(full_path)
            
            # 按页保存
            for page in pdf_info["pages"]:
                page_path = os.path.join(output_dir, f"{base_name}_page{page['page_num']}.txt")
                with open(page_path, 'w', encoding='utf-8') as f:
                    f.write(page["text"])
                file_paths.append(page_path)
            
            self.logger.info(f"已从PDF创建{len(file_paths)}个文本文件: {pdf_path}")
            return file_paths
            
        except Exception as e:
            self.logger.error(f"创建文本文件时出错: {e}")
            return []
    
    def get_statistics(self, knowledge_dir: str = "data/knowledge") -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Args:
            knowledge_dir: 知识库目录
            
        Returns:
            统计信息
        """
        stats = {
            "total_documents": 0,
            "total_text_files": 0,
            "total_pages": 0,
            "formats": {}
        }
        
        try:
            # 统计文档数量
            for root, _, files in os.walk(knowledge_dir):
                for file in files:
                    stats["total_documents"] += 1
                    ext = os.path.splitext(file)[1].lower()
                    stats["formats"][ext] = stats["formats"].get(ext, 0) + 1
                    
                    if ext == '.txt':
                        stats["total_text_files"] += 1
                    elif ext == '.pdf' and self.pdf_support:
                        try:
                            import fitz
                            pdf_path = os.path.join(root, file)
                            doc = fitz.open(pdf_path)
                            stats["total_pages"] += len(doc)
                        except:
                            pass
            
            self.logger.info(f"获取知识库统计信息: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"获取统计信息时出错: {e}")
            return stats 