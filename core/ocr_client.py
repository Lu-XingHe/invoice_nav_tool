# -*- coding: utf-8 -*-
from alibabacloud_ocr_api20210707 import models as ocr_api_20210707_models
from alibabacloud_ocr_api20210707.client import Client as ocr_api20210707Client
from alibabacloud_tea_openapi import models as open_api_models

from utils.settings import load_config


class OCRClient:
    def __init__(self):
        self._client = None
        self._config = None
        self._init_from_config()

    def _init_from_config(self):
        config = load_config()
        self._config = config
        self._build_client(config)

    def _build_client(self, config):
        # 获取当前账号
        accounts = config.get('accounts', [])
        idx = config.get('current_account', 0)
        if idx >= len(accounts):
            acc = {'access_key_id': '', 'access_key_secret': '', 'region': 'cn-hangzhou'}
        else:
            acc = accounts[idx]
        ak = acc.get('access_key_id', '')
        sk = acc.get('access_key_secret', '')
        region = acc.get('region', 'cn-hangzhou')
        endpoint = f'ocr-api.{region}.aliyuncs.com'
        if not ak or not sk:
            self._client = None
            return
        openapi_config = open_api_models.Config(
            access_key_id=ak,
            access_key_secret=sk,
            region_id=region
        )
        openapi_config.endpoint = endpoint
        self._client = ocr_api20210707Client(openapi_config)

    def refresh(self):
        self._init_from_config()

    def _ensure_client(self):
        if self._client is None:
            raise Exception("请先在设置中配置阿里云 AccessKey")

    def recognize_invoice(self, image_bytes):
        self._ensure_client()
        request = ocr_api_20210707_models.RecognizeInvoiceRequest(body=image_bytes)
        response = self._client.recognize_invoice(request)
        return response.body.to_map() if response.body else None

    def recognize_advanced(self, image_bytes):
        self._ensure_client()
        request = ocr_api_20210707_models.RecognizeAdvancedRequest(body=image_bytes)
        response = self._client.recognize_advanced(request)
        return response.body.to_map() if response.body else None

    def recognize_general(self, image_bytes):
        """
        通用文字识别（用于截图，PNG/BMP/GIF 格式支持更好）
        """
        self._ensure_client()
        request = ocr_api_20210707_models.RecognizeGeneralRequest(body=image_bytes)
        response = self._client.recognize_general(request)
        return response.body.to_map() if response.body else None

    def recognize_general_structure(self, image_bytes):
        self._ensure_client()
        request = ocr_api_20210707_models.RecognizeGeneralStructureRequest(body=image_bytes)
        response = self._client.recognize_general_structure(request)
        return response.body.to_map() if response.body else None
