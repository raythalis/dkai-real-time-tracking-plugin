# 根因与排查过程

记录这个补丁为什么需要存在，方便以后对照日志判断。

## 现象

开启实时追踪后：

- 预览区、时间轴有正常的 funscript 波形与打点，追踪算法工作正常
- 设备侧完全无动作
- 设备本身连接成功，面板显示「已连接并准备就绪」
- 界面无任何报错

## 日志证据

把程序的 `logging_level` 调到 `DEBUG`、打开设备指令日志后，可以看到三组关键信息。

### 1. 建桥时机过早

```
DEBUG - [tracker_manager._init_device_bridge:1075] - Device manager not available in app
DEBUG - [tracker_manager.__init__:144] - TrackerManager initialized - Direct modular tracker interface
```

追踪器在构造时就去建桥，而那时设备控制模块还没初始化完成，`app.device_manager` 还不存在，于是直接返回，`device_bridge` 一直是 `None`。

### 2. 补偿路径也没生效

```
INFO - [_mixin._update_existing_tracker_managers:195] - No existing TrackerManagers found to update
```

设备控制初始化完成后，本来应该回头把已有的追踪器补挂上设备管理器，但那一刻注册表是空的，一个都没找到，于是错过唯一一次补偿机会。

### 3. 发送阶段：设备管理器正常，唯独桥是空的

```
DEBUG - [tracker_manager._extract_result_data:890] - Attempting to send action to device control: {'at': 2000, 'pos': 50, 'secondary_pos': 50}
INFO  - [tracker_manager._send_to_device_control:1151] - Device manager available but no bridge - re-initializing bridge
DEBUG - [tracker_manager._send_to_device_control:1168] - Device control check: bridge=False, enabled=True, active=True
DEBUG - [tracker_manager._send_to_device_control:1170] - Device manager: exists=True, connected=True, devices=['osr_wifi_tcode.local:8000']
INFO  - [tracker_manager._send_to_device_control:1178] - Live tracking device control: No device bridge available
```

`enabled=True`、`active=True`、设备管理器在线且设备列表正确，只有 `bridge=False`。重试分支每 10 秒触发一次，但从不输出失败原因，桥始终建不起来。

整份日志里从未出现 `Live tracker bridge started and claimed device control`。

## 结论

不是设备问题，不是追踪算法问题，也不是授权问题，而是**追踪器与设备之间的 `LiveTrackerBridge` 从未被创建**，每一帧位置数据在发送前就被丢弃。

## 补丁怎么绕过去

程序虽然把这段逻辑编译进了二进制，但它的模块在运行时依然可以被导入、可以被构造。插件就是利用这一点：

1. 在进程内扫描正在运行的追踪器实例
2. 通过追踪器持有的 `app.device_manager`（此时已连接）构造 `LiveTrackerBridge`
3. `start()` 是协程，需要挂到程序自己的 asyncio 事件循环上执行
4. 把建好的桥挂回追踪器的 `device_bridge` 属性

挂上之后，程序原有的发送逻辑就会正常工作——它会自己调用 `bridge.on_tracker_result()`，最终走到 `device_manager.update_position()`，再由 OSR 后端排出 TCode 指令。

## 已验证

补丁生效后的日志：

```
INFO - [live_tracker_bridge._configure_frame_skip:95] - Live tracker bridge: Sending every ...
INFO - [live_tracker_bridge.start:118] - Live tracker bridge started and claimed device control
DEBUG - [live_tracker_bridge.on_tracker_result:191] - Bridge calling device_manager.update_position(100.0, 41.0)
DEBUG - [osr_backend.set_position:618] - Queued stroke command (v0.3): L02704I250
```

设备随追踪正常跟随。

## 已知限制

- 补丁每 2 秒扫描一次，程序新建的追踪器会在几秒内补上桥
- 如果作者的版本已经修复此问题，请删除补丁，避免重复建桥
- 程序内部结构若变化（模块名、属性名），补丁需要跟着调整
