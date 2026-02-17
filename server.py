import asyncio
import websockets
import json
import os

# إعدادات
PORT = int(os.environ.get("PORT", 10000))
connected = {}  # تخزين الأجهزة المتصلة
print(f"🚀 بدء السيرفر على المنفذ {PORT}")

async def handler(websocket):
    """معالجة اتصالات WebSocket"""
    device_id = None
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"📩 رسالة واردة: {data}")
            
            # ===== 1️⃣ تسجيل جهاز جديد =====
            if data['type'] == 'REGISTER':
                device_id = data['deviceId']
                device_name = data.get('deviceName', 'جهاز')
                connected[device_id] = websocket
                
                # رد تأكيد التسجيل
                await websocket.send(json.dumps({
                    "type": "REGISTERED",
                    "message": "تم التسجيل بنجاح",
                    "yourId": device_id
                }))
                print(f"✅ جهاز جديد: {device_name} ({device_id})")
                
                # بث قائمة الأجهزة للجميع
                await broadcast_devices()
            
            # ===== 2️⃣ طلب قائمة الأجهزة =====
            elif data['type'] == 'GET_DEVICES':
                devices_list = [{"id": id, "name": f"جهاز {id[:4]}"} for id in connected]
                await websocket.send(json.dumps({
                    "type": "DEVICE_LIST",
                    "devices": devices_list,
                    "count": len(devices_list)
                }))
                print(f"📋 تم إرسال قائمة الأجهزة ({len(devices_list)} جهاز)")
            
            # ===== 3️⃣ إرسال أمر لجهاز آخر =====
            elif data['type'] == 'COMMAND':
                target_id = data['targetId']
                command = data['command']
                from_id = data.get('fromId', 'unknown')
                
                if target_id in connected:
                    # إرسال الأمر للجهاز المستهدف
                    await connected[target_id].send(json.dumps({
                        "type": "COMMAND",
                        "command": command,
                        "fromId": from_id
                    }))
                    
                    # تأكيد للمرسل
                    await websocket.send(json.dumps({
                        "type": "COMMAND_SENT",
                        "targetId": target_id,
                        "command": command,
                        "message": "تم إرسال الأمر بنجاح"
                    }))
                    print(f"📤 أمر من {from_id} إلى {target_id}: {command}")
                else:
                    await websocket.send(json.dumps({
                        "type": "ERROR",
                        "message": "الجهاز المستهدف غير متصل"
                    }))
                    print(f"⚠️ الجهاز {target_id} غير متصل")
            
            # ===== 4️⃣ إرسال أمر للجميع =====
            elif data['type'] == 'BROADCAST':
                command = data['command']
                from_id = data.get('fromId', 'unknown')
                
                sent_count = 0
                for dev_id, ws in connected.items():
                    if dev_id != from_id:
                        try:
                            await ws.send(json.dumps({
                                "type": "COMMAND",
                                "command": command,
                                "fromId": from_id,
                                "broadcast": True
                            }))
                            sent_count += 1
                        except:
                            pass
                
                await websocket.send(json.dumps({
                    "type": "BROADCAST_SENT",
                    "count": sent_count,
                    "message": f"تم إرسال الأمر إلى {sent_count} جهاز"
                }))
                print(f"📢 بث من {from_id} إلى {sent_count} جهاز: {command}")
            
            # ===== 5️⃣ أمر غير معروف =====
            else:
                await websocket.send(json.dumps({
                    "type": "ERROR",
                    "message": f"أمر غير معروف: {data['type']}"
                }))
    
    except websockets.exceptions.ConnectionClosed:
        print(f"🔴 قطع الاتصال: {device_id}")
    finally:
        if device_id and device_id in connected:
            del connected[device_id]
            await broadcast_devices()

async def broadcast_devices():
    """بث قائمة الأجهزة لكل الأجهزة المتصلة"""
    devices_list = [{"id": id, "name": f"جهاز {id[:4]}"} for id in connected]
    message = json.dumps({
        "type": "DEVICE_LIST",
        "devices": devices_list,
        "count": len(devices_list)
    })
    
    disconnected = []
    for dev_id, ws in connected.items():
        try:
            await ws.send(message)
        except:
            disconnected.append(dev_id)
    
    for dev_id in disconnected:
        if dev_id in connected:
            del connected[dev_id]
    
    if disconnected:
        print(f"🧹 تم تنظيف {len(disconnected)} جهاز غير متصل")

async def health_check(path, request_headers):
    """فحص صحي لـ Render"""
    if path == "/":
        return websockets.http.Headers(), 200, b"Server is running"

async def main():
    """تشغيل السيرفر"""
    print("=" * 50)
    print("🚀 سيرفر التحكم - جاهز للعمل")
    print("=" * 50)
    print(f"📡 المنفذ: {PORT}")
    print(f"🌐 للإتصال: wss://your-server.onrender.com")
    print(f"📋 الأوامر المدعومة: REGISTER, GET_DEVICES, COMMAND, BROADCAST")
    print("=" * 50)
    
    async with websockets.serve(
        handler, 
        "0.0.0.0", 
        PORT,
        process_request=health_check
    ):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف السيرفر")
    except Exception as e:
        print(f"❌ خطأ: {e}")
