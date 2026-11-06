# DKAI-FunStudio 实时追踪插件

修复 **DKAI-FunStudio 2.1.7 Beta.7** 的一个问题：开启实时追踪后，预览有波形、时间轴有点，但连接的设备（OSR / TCode）完全不动。

不改程序本体、不改 exe。用的是程序自带的 `user_plugins` 插件机制，在它进程内把缺失的「实时桥」补建出来。

---

## 一、先确认你是不是这个问题

打开程序目录下的 `logs\dkai.log`，搜索：

```
Device manager available but no bridge - re-initializing bridge
Live tracking device control: No device bridge available
```

如果这两句每 10 秒出现一次、而且整份日志里搜不到 `Live tracker bridge started`，就是本插件针对的问题。

同时符合：设备显示已连接、追踪波形正常、设备一动不动。

---

## 二、安装

1. 完全关闭 DKAI-FunStudio
2. 把仓库里的三个文件复制到 **程序目录\user_plugins\**：
   - `dk_bridge_host.py`
   - `dk_bridge_ext.py`
   - `PATCH_GO.txt`
3. 重新打开程序

> 程序目录 = `DKAI-FunStudio.exe` 所在那一层，里面应当有 `user_plugins` 文件夹。

---

## 三、使用

照常连接设备、照常开实时追踪。设备应该会跟着动。

插件是全自动的：每 2 秒检查一次，发现追踪器没有桥就补一条；程序新创建的追踪器也会自动补上，不需要任何手动操作。

---

## 四、验证生效

看 `user_plugins\dk_bridge_ext.log`：

```
PATCH: created LiveTrackerBridge
PATCH: start() -> True
PATCH: attached on id=xxxxx active=True
```

同时 `logs\dkai.log` 里会出现：

```
Live tracker bridge started and claimed device control
Bridge calling device_manager.update_position(...)
```

---

## 五、关闭 / 卸载

- **临时关闭**：删掉 `user_plugins\PATCH_GO.txt`，不用重启程序，几秒内停止补桥
- **彻底卸载**：删掉三个文件，重启程序
- 插件不修改程序本体、不改设置，删掉即恢复原样

---

## 六、常见问题

**装完还是不动？**
先确认设备在设备控制面板里显示「已连接」，再开追踪。插件只负责补桥，设备没连上它也发不出去。

**动了但很慢、跟不上手？**
这是程序自己的发送节流造成的，调设备控制里的 OSR 性能设置（灵敏度、速度）即可，和插件无关。

**作者出了新版本？**
先删掉这三个文件再升级。新版可能已经修好，重复补桥会导致指令重复发送。

**会崩吗？**
插件全程包了异常处理，出错只写日志不抛给程序。真出问题删掉三个文件重启即恢复。

**日志在哪？**

| 文件 | 内容 |
|---|---|
| `user_plugins\dk_bridge_host.log` | 插件加载、热更新记录 |
| `user_plugins\dk_bridge_ext.log` | 补桥过程、桥状态 |
| `logs\dkai.log` | 程序自身日志（日志级别调成 DEBUG 能看到发送细节） |

---

## 七、兼容性

- 只在 **Windows / DKAI-FunStudio 2.1.7 Beta.7** 上验证过
- 依赖程序内部的 `device_control.bridges.live_tracker_bridge` 模块，其他版本结构可能不同
- `dk_bridge_ext.py` 支持热修改：改完保存，插件自动重新加载，不用重启程序

根因分析和排查过程见 [docs/root-cause.md](docs/root-cause.md)。

---

## 免责声明

非官方补丁，与程序作者无关，仅供遇到相同问题的用户临时自救。程序更新后请优先使用官方修复。
