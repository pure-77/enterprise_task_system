# 腾讯云数据万象文档预览配置指南

## 功能说明

本系统支持使用腾讯云数据万象（Cloud Infinite，CI）进行Office文档在线预览，支持以下格式：
- Word文档（.doc, .docx）
- Excel表格（.xls, .xlsx）
- PowerPoint演示文稿（.ppt, .pptx）

## 配置步骤

### 第一步：注册腾讯云账号

1. 访问 [腾讯云官网](https://cloud.tencent.com/)
2. 注册账号并完成实名认证

### 第二步：开通数据万象服务

1. 访问 [数据万象控制台](https://console.cloud.tencent.com/ci)
2. 点击"立即开通"
3. 阅读并同意服务协议

### 第三步：创建COS存储桶

1. 访问 [COS控制台](https://console.cloud.tencent.com/cos)
2. 点击"创建存储桶"
3. 填写配置：
   - **名称**：例如 `my-docs-preview`
   - **地域**：选择离你最近的地域（例如 `ap-guangzhou`）
   - **访问权限**：建议选择"公有读私有写"
4. 点击"确定"创建

### 第四步：获取API密钥

1. 访问 [API密钥管理](https://console.cloud.tencent.com/cam/capi)
2. 点击"新建密钥"
3. 记录生成的 **SecretId** 和 **SecretKey**

### 第五步：配置环境变量

在项目根目录的 `.env` 文件中添加以下配置：

```env
# 腾讯云COS配置
COS_SECRET_ID=你的SecretId
COS_SECRET_KEY=你的SecretKey
COS_BUCKET=你的存储桶名称（例如：my-docs-preview）
COS_REGION=你的地域（例如：ap-guangzhou）
COS_APPID=你的APPID（在COS控制台可以看到）
```

### 第六步：安装Python依赖

```bash
cd backend
pip install -r requirements.txt
```

或者单独安装COS SDK：

```bash
pip install cos-python-sdk-v5
```

## 使用说明

### 预览文档

1. 上传Office文档到系统
2. 点击文档的"预览"按钮
3. 系统会自动使用腾讯云数据万象进行预览
4. 如果腾讯云预览失败，会自动回退到其他预览方式

### 预览效果

腾讯云数据万象会将Office文档转换为HTML5页面，支持：
- ✅ 完整的格式保留
- ✅ 图片和图表显示
- ✅ 表格样式
- ✅ 动画效果（PPT）
- ✅ 响应式布局

## 费用说明

腾讯云数据万象的计费方式：

### 存储费用
- 按COS存储容量计费
- 价格：约 ¥0.118/GB/月（标准存储）

### 请求费用
- 按请求次数计费
- 价格：约 ¥0.01/万次

### 数据处理费用
- 文档预览按次数计费
- 价格：约 ¥0.1/千次

### 免费额度
- 新用户通常有一定的免费额度
- 具体额度请查看 [腾讯云定价页面](https://cloud.tencent.com/document/product/460/8291)

## 常见问题

### Q1: 预览失败怎么办？

A: 系统会自动回退到其他预览方式：
1. LibreOffice转换PDF（如果已安装）
2. 第三方预览服务（XDOC、Google Docs）
3. 直接下载文件

### Q2: 如何检查COS配置是否正确？

A: 可以在后端日志中查看相关错误信息，或者访问COS控制台检查存储桶状态。

### Q3: 支持哪些文件格式？

A: 目前支持以下格式：
- Word: .doc, .docx
- Excel: .xls, .xlsx
- PowerPoint: .ppt, .pptx

### Q4: 文件大小有限制吗？

A: 腾讯云数据万象支持的文件大小限制：
- Word: 最大 200MB
- Excel: 最大 200MB
- PowerPoint: 最大 200MB

### Q5: 预览链接会过期吗？

A: 预览链接有时效性，默认24小时。过期后需要重新获取。

## 技术支持

如果遇到问题，可以：
1. 查看 [腾讯云数据万象文档](https://cloud.tencent.com/document/product/460)
2. 提交工单到腾讯云技术支持
3. 在项目GitHub提交Issue

## 安全建议

1. **不要将API密钥提交到代码仓库**
2. **使用环境变量管理敏感信息**
3. **定期轮换API密钥**
4. **设置COS存储桶的访问权限**
5. **启用COS的访问日志功能**
