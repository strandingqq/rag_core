# API Tests

当前测试使用 Python 标准库 `unittest`，不依赖 `pytest`。

从项目根目录运行全部测试：

```powershell
python -m unittest discover api/tests
```

运行单个测试文件：

```powershell
python -m unittest api.tests.test_health
python -m unittest api.tests.test_session_store
python -m unittest api.tests.test_planner
python -m unittest api.tests.test_interview_api
```

这些测试不会真实调用 Chroma 或 LLM。涉及外部依赖的地方使用 fake object 或 monkey patch 替代。

