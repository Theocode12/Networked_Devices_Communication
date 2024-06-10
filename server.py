from aiohttp import web
import json

data = {
    "System_Status": "Okay",
    "Vbat": 34,
    "BuckCurr": 44,
    "BusVolt": 12,
    "PoutVA": 2000,
    "Load_Percentage(%)": 40,
    "Inverter_Current(A)": 4,
    "PoutW": 300,
    "AC_Output_Frequency(Hz)": 50,
    "AC_Output_Voltage(V)": 50,
    "Bus_Voltage": 3,
    "Battery_Discharge_Today(kWH)": 2,
    "Battery_Watts(W)": 40,
    "Vpv": 3,
    "LocalLoadEnergyToday": 20,
    "LocalLoadEnergyTotal": 400,
    "Ppv": 200,
}


async def hello(request):
    return web.Response(text="Hello, world")


async def inverter_response(request):
    return web.json_response(data=data)


if __name__ == "__main__":
    app = web.Application()
    app.add_routes([web.get("/", hello), web.get("/status", inverter_response)])
    web.run_app(app)
