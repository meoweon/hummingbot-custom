import logging
import os

from fastapi import APIRouter, HTTPException

from models import HummingbotInstanceConfig, ImageName
from services.bot_archiver import BotArchiver
from services.docker_service import DockerManager

router = APIRouter(tags=["Docker Management"])
docker_manager = DockerManager()
bot_archiver = BotArchiver(
    os.environ.get("AWS_API_KEY"), os.environ.get("AWS_SECRET_KEY"), os.environ.get("S3_DEFAULT_BUCKET_NAME")
)


@router.get("/is-docker-running")
async def is_docker_running():
    return {"is_docker_running": docker_manager.is_docker_running()}


@router.get("/available-images/{image_name}")
async def available_images(image_name: str):
    available_images = docker_manager.get_available_images()
    image_tags = [tag for image in available_images["images"] for tag in image.tags if image_name in tag]
    return {"available_images": image_tags}


@router.get("/active-containers")
async def active_containers():
    return docker_manager.get_active_containers()


@router.get("/exited-containers")
async def exited_containers():
    return docker_manager.get_exited_containers()


@router.post("/clean-exited-containers")
async def clean_exited_containers():
    return docker_manager.clean_exited_containers()


@router.post("/remove-container/{container_name}")
async def remove_container(container_name: str, archive_locally: bool = True, s3_bucket: str = None):
    print(f"接收到移除容器请求: {container_name}")
    try:
        # 移除容器
        try:
            print(f"尝试移除容器: {container_name}")
            response = docker_manager.remove_container(container_name)
            print(f"移除容器结果: {response}")
            if not response.get("success", False):
                print(f"移除容器失败: {response.get('message', '未知错误')}")
                # 继续尝试归档，即使容器移除失败
        except Exception as e:
            print(f"移除容器时出错: {str(e)}")
            response = {"success": False, "message": f"移除容器出错: {str(e)}"}
            # 继续尝试归档，即使容器移除失败

        # 设置实例目录路径
        instance_dir = os.path.join("bots", "instances", container_name)

        # 归档数据
        try:
            print(f"尝试归档数据: {container_name}")
            if archive_locally:
                bot_archiver.archive_locally(container_name, instance_dir)
                print(f"本地归档完成: {container_name}")
            else:
                bot_archiver.archive_and_upload(container_name, instance_dir, bucket_name=s3_bucket)
                print(f"S3归档完成: {container_name}")
        except Exception as e:
            print(f"归档数据时出错: {str(e)}")
            # 不抛出异常，而是添加到响应中
            if isinstance(response, dict):
                response["archive_error"] = str(e)
            else:
                response = {"success": False, "message": str(response), "archive_error": str(e)}

        print(f"容器 {container_name} 移除和归档操作完成")
        return response
    except Exception as e:
        error_msg = f"处理移除容器请求时发生未处理异常: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}


@router.post("/stop-container/{container_name}")
async def stop_container(container_name: str):
    print(f"接收到停止容器请求: {container_name}")
    try:
        print(f"尝试停止容器: {container_name}")
        result = docker_manager.stop_container(container_name)
        print(f"停止容器结果: {result}")

        # 如果stop_container返回一个字符串，则它是一个错误消息
        if isinstance(result, str):
            print(f"停止容器时出错: {result}")
            return {"success": False, "message": result}

        print(f"容器 {container_name} 停止操作完成")
        return {"success": True, "message": f"Container {container_name} stopped successfully."}
    except Exception as e:
        error_msg = f"停止容器时发生未处理异常: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}


@router.post("/start-container/{container_name}")
async def start_container(container_name: str):
    return docker_manager.start_container(container_name)


@router.post("/create-hummingbot-instance")
async def create_hummingbot_instance(config: HummingbotInstanceConfig):
    logging.info(f"Creating hummingbot instance with config: {config}")
    response = docker_manager.create_hummingbot_instance(config)
    return response


@router.post("/pull-image/")
async def pull_image(image: ImageName):
    try:
        result = docker_manager.pull_image(image.image_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
