import os
import uuid
from datetime import datetime
from flask import current_app
import oss2


class OSSService:
    """阿里云OSS服务类"""
    
    def __init__(self):
        self.access_key_id = current_app.config.get('OSS_ACCESS_KEY_ID')
        self.access_key_secret = current_app.config.get('OSS_ACCESS_KEY_SECRET')
        self.endpoint = current_app.config.get('OSS_ENDPOINT')
        self.bucket_name = current_app.config.get('OSS_BUCKET_NAME')
        
        if not all([self.access_key_id, self.access_key_secret, self.endpoint, self.bucket_name]):
            raise ValueError("OSS配置信息不完整，请检查config.py中的OSS配置")
        
        # 创建Auth对象
        self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        # 创建Bucket对象
        self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)
    
    def upload_avatar(self, file_data: bytes, file_extension: str, user_id: int) -> str:
        """
        上传头像文件到OSS
        
        Args:
            file_data: 文件二进制数据
            file_extension: 文件扩展名 (如: .jpg, .png)
            user_id: 用户ID
            
        Returns:
            str: 上传成功后的文件URL
        """
        try:
            # 生成唯一的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"avatars/{user_id}/{timestamp}_{unique_id}{file_extension}"
            
            # 上传文件
            result = self.bucket.put_object(filename, file_data)
            
            if result.status == 200:
                # 返回文件的公网访问URL
                file_url = f"{self.endpoint.replace('https://', f'https://{self.bucket_name}.')}/{filename}"
                return file_url
            else:
                raise Exception(f"上传失败，状态码: {result.status}")
                
        except Exception as e:
            current_app.logger.error(f"OSS上传失败: {str(e)}")
            raise e
    
    def delete_avatar(self, file_url: str) -> bool:
        """
        删除OSS中的头像文件
        
        Args:
            file_url: 文件的完整URL
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 从URL中提取文件路径
            if self.bucket_name in file_url:
                from urllib.parse import urlparse
                # 使用urlparse解析URL
                parsed_url = urlparse(file_url)
                # 验证URL路径是否包含bucket_name
                if parsed_url.path.startswith(f"/{self.bucket_name}/"):
                    # 提取文件在OSS中的路径
                    file_path = parsed_url.path[len(f"/{self.bucket_name}/"):]
                    # 删除文件
                    result = self.bucket.delete_object(file_path)
                return result.status == 204
            else:
                current_app.logger.warning(f"无效的文件URL: {file_url}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"OSS删除失败: {str(e)}")
            return False
    
    @staticmethod
    def validate_image_file(file_data: bytes, max_size: int = 5 * 1024 * 1024) -> tuple[bool, str]:
        """
        验证图片文件
        
        Args:
            file_data: 文件二进制数据
            max_size: 最大文件大小（字节），默认5MB
            
        Returns:
            tuple: (是否有效, 错误信息或文件扩展名)
        """
        if len(file_data) == 0:
            return False, "文件内容为空"
        
        if len(file_data) > max_size:
            return False, f"文件大小超过限制 ({max_size / 1024 / 1024:.1f}MB)"
        
        # 检查文件头部，判断文件类型
        file_signatures = {
            b'\xff\xd8\xff': '.jpg',
            b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a': '.png',
            b'GIF87a': '.gif',
            b'GIF89a': '.gif',
            b'RIFF': '.webp'  # WebP文件通常以RIFF开头
        }
        
        for signature, extension in file_signatures.items():
            if file_data.startswith(signature):
                return True, extension
        
        # 特殊处理WebP
        if file_data.startswith(b'RIFF') and b'WEBP' in file_data[:20]:
            return True, '.webp'
        
        return False, "不支持的文件格式，仅支持 JPG, PNG, GIF, WebP"