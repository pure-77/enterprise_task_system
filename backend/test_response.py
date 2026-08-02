"""测试统一响应格式"""
from app.shared.response import success_response, error_response, paginated_response


def test_success_response_with_data():
    result = success_response({"name": "test"})
    assert result["code"] == 0
    assert result["message"] == "success"
    assert result["data"]["name"] == "test"


def test_success_response_no_data():
    result = success_response()
    assert result["code"] == 0
    assert result["data"] is None


def test_error_response():
    result = error_response(code=40401, message="资源不存在", detail="Task id=99 not found")
    assert result["code"] == 40401
    assert result["message"] == "资源不存在"
    assert result["detail"] == "Task id=99 not found"


def test_paginated_response():
    result = paginated_response(items=[1, 2, 3], total=30, page=2, page_size=10)
    assert result["code"] == 0
    assert result["data"]["items"] == [1, 2, 3]
    assert result["data"]["total"] == 30
    assert result["data"]["page"] == 2
    assert result["data"]["total_pages"] == 3


if __name__ == "__main__":
    test_success_response_with_data()
    test_success_response_no_data()
    test_error_response()
    test_paginated_response()
    print("All tests passed!")
