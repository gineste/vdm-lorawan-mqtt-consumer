import base64
import math


class CatenaDecoder :
    def __init__ ( self ) :
        pass

    def parse ( self , port, b64Str ) :
        b64arr = base64.standard_b64decode(b64Str)
        return self.decode(port, b64arr)


    # Decode decodes an array of bytes into an object.
    #  - fPort contains the LoRaWAN fPort number
    #  - bytes is an array of bytes, e.g. [225, 230, 255, 0]
    # The function must return an object, e.g.:"temperature": 22.5
    # This function decodes the records (port 1, format 0x11, 0x14, 0x15, 0x16, 0x17)
    # sent by the MCCI Catena 4410/4450/4551 soil/water and power applications.
    # For use with console.thethingsnetwork.org
    # 2017-09-19 add dewpoints.
    # 2017-12-13 fix commments, fix negative soil/water temp, add test vectors.
    # 2017-12-15 add format 0x11.
    # 2018-04-24 add format 0x16.
    # 2018-04-01 add format 0x17.
    # 2018-06-13 add air quality.
    # 2019-02-13 add simple sensor format (port 2).
    # 2019-06-28 add port 3 (no barometric pressure)

    # calculate dewpoint (degrees C) given temperature (C) and relative humidity (0..100)
    # from http:#andrew.rsmas.miami.edu/bmcnoldy/Humidity.html
    # rearranged for efficiency and to deal sanely with very low (< 1%) RH
    def dewpoint ( self , t , rh ) :
        c1 = 243.04
        c2 = 17.625
        h = rh / 100
        if (h <= 0.01):
            h = 0.01
        elif (h > 1.0):
            h = 1.0

        lnh = math.log ( h )
        tpc1 = t + c1
        txc2 = t * c2
        txc2_tpc1 = txc2 / tpc1

        tdew = c1 * (lnh + txc2_tpc1) / (c2 - lnh - txc2_tpc1)
        return tdew


    # Calculate Water Level.

    def waterlevel ( self , wp ) :
        ρ = 1000
        g = 9.81
        h = (wp * 1000) / (ρ * g)
        return h


    def decode ( self , port , bytes ) :
        # Decode an uplink message from a buffer
        # (array) of bytes to an object of fields.
        decoded = {}

        if (port == 1) :
            cmd = bytes [ 0 ]
            if (cmd == 0x14) :
                # decode Catena 4450 M101 data

                # test vectors:
                #  14 01 18 00 ==> vBat = 1.5
                #  14 01 F8 00 ==> vBat = -0.5
                #  14 05 F8 00 42 ==> boot: 66, vBat: -0.5
                #  14 0D F8 00 42 17 80 59 35 80 ==> adds one temp of 23.5, rh = 50, p = 913.48

                # i is used as the index into the message. Start with the flag byte.
                i = 1
                # fetch the bitmap.
                flags = bytes [ i ]
                i += 1

                if (flags & 0x1) :
                    # set vRaw to a uint16, and increment pointer
                    vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    # interpret uint16 as an int16 instead.
                    if (vRaw & 0x8000):
                        vRaw += -0x10000
                    # scale and save in decoded["
                    decoded["vBat"] = vRaw / 4096.0

                if (flags & 0x2) :
                    vRawBus = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (vRawBus & 0x8000):
                        vRawBus += -0x10000
                    decoded["vBus"] = vRawBus / 4096.0

                if (flags & 0x4) :
                    iBoot = bytes [ i ]
                    i += 1
                    decoded["boot"] = iBoot

                if (flags & 0x8) :
                    # we have temp, pressure, RH
                    tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    if (tRaw & 0x8000):
                        tRaw = -0x10000 + tRaw
                    i += 2
                    pRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    hRaw = bytes [ i ]
                    i += 1

                    decoded["tempC"] = tRaw / 256
                    decoded["error"] = "none"
                    decoded["p"] = pRaw * 4 / 100.0
                    decoded["rh"] = hRaw / 256 * 100
                    decoded["tDewC"] = self.dewpoint ( decoded["tempC"] , decoded["rh"] )

                if (flags & 0x10) :
                    # we have lux
                    luxRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["lux"] = luxRaw

                if flags & 0x20 :
                    # watthour
                    powerIn = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    powerOut = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["powerUsedCount"] = powerIn
                    decoded["powerSourcedCount"] = powerOut

                if flags & 0x40 :
                    # normalize floating pulses per hour
                    floatIn = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    floatOut = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2

                    exp1 = floatIn >> 12
                    exp2 = floatOut >> 12
                    mant1 = (floatIn & 0xFFF) / 4096.0
                    mant2 = (floatOut & 0xFFF) / 4096.0
                    powerPerHourIn = mant1 * pow ( 2 , exp1 - 15 ) * 60 * 60 * 4
                    powerPerHourOut = mant2 * pow ( 2 , exp2 - 15 ) * 60 * 60 * 4
                    decoded["powerUsedPerHour"] = powerPerHourIn
                    decoded["powerSourcedPerHour"] = powerPerHourOut

            elif (cmd == 0x15) :
                # decode Catena 4450 M102 data

                # test vectors:
                #  15 01 18 00 ==> vBat = 1.5
                #  15 01 F8 00 ==> vBat = -0.5
                #  15 05 F8 00 42 ==> boot: 66, vBat: -0.5
                #  15 0D F8 00 42 17 80 59 35 80 ==> adds one temp of 23.5, rh = 50, p = 913.48, tDewC = 12.5
                #  15 7D 44 60 0D 15 9D 5F CD C3 00 00 1C 11 14 46 E4 ==>
                #	{
                #    "boot": 13,
                #    "error": "none",
                #    "lux": 0,
                #    "p": 981,
                #    "rh": 76.171875,
                #    "rhSoil": 89.0625,
                #    "tDewC": 17.236466758309017,
                #    "tSoil": 20.2734375,
                #    "tSoilDew": 18.411840342527178,
                #    "tWater": 28.06640625,
                #    "tempC": 21.61328125,
                #    "vBat": 4.2734375,
                #
                # 15 7D 43 72 07 17 A4 5F CB A7 01 DB 1C 01 16 AF C3
                #   :
                #    "boot": 7,
                #    "error": "none",
                #    "lux": 475,
                #    "p": 980.92,
                #    "rh": 65.234375,
                #    "rhSoil": 76.171875,
                #    "tDewC": 16.732001483771757,
                #    "tSoil": 22.68359375,
                #    "tSoilDew": 18.271601276518467,
                #    "tWater": 28.00390625,
                #    "tempC": 23.640625,
                #    "vBat": 4.21533203125
                #
                # 15 7D 42 D4 21 F5 9B 5E 5F C1 00 00 01 C1 F9 1B EC
                #   :
                #    "boot": 33,
                #    "error": "none",
                #    "lux": 0,
                #    "p": 966.36,
                #    "rh": 75.390625,
                #    "rhSoil": 92.1875,
                #    "tDewC": -13.909882718758952,
                #    "tSoil": -6.89453125,
                #    "tSoilDew": -7.948780789914008,
                #    "tWater": 1.75390625,
                #    "tempC": -10.39453125,
                #    "vBat": 4.1767578125
                #
                # i is used as the index into the message. Start with the flag byte.
                i = 1
                # fetch the bitmap.
                flags = bytes [ i ]
                i += 1

                if (flags & 0x1) :
                    # set vRaw to a uint16, and increment pointer
                    vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    # interpret uint16 as an int16 instead.
                    if (vRaw & 0x8000):
                        vRaw += -0x10000
                    # scale and save in decoded["
                    decoded["vBat"] = vRaw / 4096.0

                if (flags & 0x2) :
                    vRawBus = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (vRawBus & 0x8000):
                        vRawBus += -0x10000
                    decoded["vBus"] = vRawBus / 4096.0

                if (flags & 0x4) :
                    iBoot = bytes [ i ]
                    i += 1
                    decoded["boot"] = iBoot

                if (flags & 0x8) :
                    # we have temp, pressure, RH
                    tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    if (tRaw & 0x8000):
                        tRaw = -0x10000 + tRaw
                    i += 2
                    pRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    hRaw = bytes [ i ]
                    i += 1

                    decoded["tempC"] = tRaw / 256
                    decoded["error"] = "none"
                    decoded["p"] = pRaw * 4 / 100.0
                    decoded["rh"] = hRaw / 256 * 100
                    decoded["tDewC"] = self.dewpoint( decoded["tempC"] , decoded["rh"] )

                if (flags & 0x10) :
                    # we have lux
                    luxRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["lux"] = luxRaw

                if (flags & 0x20) :
                    # onewire temperature
                    tempRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (tempRaw & 0x8000):
                        tempRaw = -0x10000 + tempRaw
                    decoded["tWater"] = tempRaw / 256

                if (flags & 0x40) :
                    # temperature followed by RH
                    tempRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (tempRaw & 0x8000):
                        tempRaw = -0x10000 + tempRaw
                    tempRH = bytes [ i ]
                    i += 1
                    decoded["tSoil"] = tempRaw / 256
                    decoded["rhSoil"] = tempRH / 256 * 100
                    decoded["tSoilDew"] = self.dewpoint ( decoded["tSoil"] , decoded["rhSoil"] )

            elif (cmd == 0x11) :
                # decode Catena 4410 sensor data

                # test vectors:
                #  11 01 18 00 ==> vBat = 1.5
                #  11 01 F8 00 ==> vBat = -0.5
                #  11 05 F8 00 17 80 59 35 80 ==> adds one temp of 23.5, rh = 50, p = 913.48, tDewC = 12.5
                #  11 3D 44 60 15 9D 5F CD C3 00 00 1C 11 14 46 E4 ==>
                #	{
                #    "error": "none",
                #    "lux": 0,
                #    "p": 981,
                #    "rh": 76.171875,
                #    "rhSoil": 89.0625,
                #    "tDewC": 17.236466758309017,
                #    "tSoil": 20.2734375,
                #    "tSoilDew": 18.411840342527178,
                #    "tWater": 28.06640625,
                #    "tempC": 21.61328125,
                #    "vBat": 4.2734375,
                #
                # 11 3D 43 72 17 A4 5F CB A7 01 DB 1C 01 16 AF C3
                #   :
                #    "error": "none",
                #    "lux": 475,
                #    "p": 980.92,
                #    "rh": 65.234375,
                #    "rhSoil": 76.171875,
                #    "tDewC": 16.732001483771757,
                #    "tSoil": 22.68359375,
                #    "tSoilDew": 18.271601276518467,
                #    "tWater": 28.00390625,
                #    "tempC": 23.640625,
                #    "vBat": 4.21533203125
                #
                # i is used as the index into the message. Start with the flag byte.
                i = 1
                # fetch the bitmap.
                flags = bytes [ i ]
                i += 1

                if (flags & 0x1) :
                    # set vRaw to a uint16, and increment pointer
                    vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    # interpret uint16 as an int16 instead.
                    if (vRaw & 0x8000):
                        vRaw += -0x10000
                    # scale and save in decoded["
                    decoded["vBat"] = vRaw / 4096.0

                if (flags & 0x2) :
                    vRawBus = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (vRawBus & 0x8000):
                        vRawBus += -0x10000
                    decoded["vBus"] = vRawBus / 4096.0

                if (flags & 0x4) :
                    # we have temp, pressure, RH
                    tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    if (tRaw & 0x8000):
                        tRaw = -0x10000 + tRaw
                    i += 2
                    pRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    hRaw = bytes [ i ]
                    i += 1

                    decoded["tempC"] = tRaw / 256
                    decoded["error"] = "none"
                    decoded["p"] = pRaw * 4 / 100.0
                    decoded["rh"] = hRaw / 256 * 100
                    decoded["tDewC"] = self.dewpoint ( decoded["tempC"] , decoded["rh"] )

                if (flags & 0x8) :
                    # we have lux
                    luxRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["lux"] = luxRaw

                if (flags & 0x10) :
                    # onewire temperature
                    tempRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["tWater"] = tempRaw / 256

                if flags & 0x20 :
                    # temperature followed by RH
                    tempRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    tempRH = bytes [ i ]
                    i += 1
                    decoded["tSoil"] = tempRaw / 256
                    decoded["rhSoil"] = tempRH / 256 * 100
                    decoded["tSoilDew"] = self.dewpoint ( decoded["tSoil"] , decoded["rhSoil"] )

            elif cmd == 0x16 :

                # decode Catena 4450 Water Level data

                # test vectors:
                #  17 01 18 00 ==> vBat = 1.5
                #  17 01 F8 00 ==> vBat = -0.5
                #  17 05 F8 00 42 ==> boot: 66, vBat: -0.5
                #  17 0D F8 00 42 17 80 59 35 80 ==> adds one temp of 23.5, rh = 50, p = 913.48
                #  16 3D 46 F4 59 1E CB 62 9F 68 00 F7 67 85 ==>
                #	{
                #    "water pressure": 01.805
                #    "boot": 89,
                #    "error": "none",
                #    "lux": 247,
                #    "p": 1009.88,
                #    "rh": 40.625,
                #    "tempC": 30.792,
                #    "vBat": 4.434,
                #

                # i is used as the index into the message. Start with the flag byte.

                i = 1
                # fetch the bitmap.
                flags = bytes [ i ]
                i += 1

                if (flags & 0x1) :
                    # set vRaw to a uint16, and increment pointer
                    vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    # interpret uint16 as an int16 instead.
                    if (vRaw & 0x8000):
                        vRaw += -0x10000
                    # scale and save.
                    decoded["vBat"] = vRaw / 4096.0

                if (flags & 0x2) :
                    vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (vRaw & 0x8000):
                        vRaw += -0x10000
                    decoded["vBus"] = vRaw / 4096.0

                if (flags & 0x4) :
                    iBoot = bytes [ i ]
                    i += 1
                    decoded["boot"] = iBoot

                if (flags & 0x8) :
                    # we have temp, pressure, RH
                    tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    if (tRaw & 0x8000):
                        tRaw = -0x10000 + tRaw
                    i += 2
                    pRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    hRaw = bytes [ i ]
                    i += 1

                    decoded["t"] = tRaw / 256
                    decoded["p"] = pRaw * 4 / 100.0
                    decoded["rh"] = hRaw / 256 * 100

                if (flags & 0x10) :
                    # we have lux
                    luxRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["lux"] = luxRaw

                if (flags & 0x20) :
                    # Decode Rayco Sensor Data.
                    wpRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    # Convert pressure from hPa to kPa. And display payload.
                    decoded["wPressure"] = (wpRaw * 4 / 100.0) / 10
                    decoded["wLevel"] = self.waterlevel ( decoded["wPressure"] )


            elif (cmd == 0x17) :
                # decode Catena 4460 AQI data

                # test vectors:
                #  17 01 18 00 ==> vBat = 1.5
                #  17 01 F8 00 ==> vBat = -0.5
                #  17 05 F8 00 42 ==> boot: 66, vBat: -0.5
                #  17 0D F8 00 42 17 80 59 35 80 ==> adds one temp of 23.5, rh = 50, p = 913.48, tDewC = 12.5
                #  17 3D 44 60 0D 15 9D 5F CD C3 00 00 F9 07 ==>
                #	{
                #    "aqi": 288.875
                #    "boot": 13,
                #    "error": "none",
                #    "lux": 0,
                #    "p": 981,
                #    "rh": 76.171875,
                #    "tDewC": 17.236466758309017,
                #    "tempC": 21.61328125,
                #    "vBat": 4.2734375,
                #
                # 17 3D 43 72 07 17 A4 5F CB A7 01 DB E9 AF ==>
                #   :
                #    "aqi": 154.9375,
                #    "boot": 7,
                #    "error": "none",
                #    "lux": 475,
                #    "p": 980.92,
                #    "rh": 65.234375,
                #    "tDewC": 16.732001483771757,
                #    "tempC": 23.640625,
                #    "vBat": 4.21533203125
                #
                # 17 FD 3C 05 53 16 EE 61 F1 94 00 A7 DB 91 EB F7 03 ==>
                #   :
                #    "boot": 83,
                #    "error": "none",
                #    "iaq": 92.53125,
                #    "iaqQuality": 3,
                #    "log_r_gas": 5.982421875,
                #    "lux": 167,
                #    "p": 1002.92,
                #    "r_gas": 960333.0490535165,
                #    "rh": 57.8125,
                #    "tDewC": 14.178238315794754,
                #    "tempC": 22.9296875,
                #    "vBat": 3.751220703125
                #

                # i is used as the index into the message. Start with the flag byte.
                i = 1
                # fetch the bitmap.
                flags = bytes [ i ]
                i += 1

                if (flags & 0x1) :
                    # set vRaw to a uint16, and increment pointer
                    vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    # interpret uint16 as an int16 instead.
                    if (vRaw & 0x8000):
                        vRaw += -0x10000
                    # scale and save in decoded["
                    decoded["vBat"] = vRaw / 4096.0

                if (flags & 0x2) :
                    vRawBus = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    if (vRawBus & 0x8000):
                        vRawBus += -0x10000
                    decoded["vBus"] = vRawBus / 4096.0

                if (flags & 0x4) :
                    iBoot = bytes [ i ]
                    i += 1
                    decoded["boot"] = iBoot

                if (flags & 0x8) :
                    # we have temp, pressure, RH
                    tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    if (tRaw & 0x8000):
                        tRaw = -0x10000 + tRaw
                    i += 2
                    pRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    hRaw = bytes [ i ]
                    i += 1

                    decoded["tempC"] = tRaw / 256
                    decoded["error"] = "none"
                    decoded["p"] = pRaw * 4 / 100.0
                    decoded["rh"] = hRaw / 256 * 100
                    decoded["tDewC"] = self.dewpoint ( decoded["tempC"] , decoded["rh"] )

                if (flags & 0x10) :
                    # we have lux
                    luxRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2
                    decoded["lux"] = luxRaw

                if (flags & 0x20) :
                    rawUflt16 = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2

                    exp1 = rawUflt16 >> 12
                    mant1 = (rawUflt16 & 0xFFF) / 4096.0
                    f_unscaled = mant1 * pow ( 2 , exp1 - 15 )
                    aqi = f_unscaled * 512

                    decoded["iaq"] = aqi

                if (flags & 0x40) :
                    rawUflt16 = (bytes [ i ] << 8) + bytes [ i + 1 ]
                    i += 2

                    exp1 = rawUflt16 >> 12
                    mant1 = (rawUflt16 & 0xFFF) / 4096.0
                    f_unscaled = mant1 * pow ( 2 , exp1 - 15 )

                    logGasR = f_unscaled * 16
                    gasR = pow ( 10 , logGasR )
                    decoded["log_r_gas"] = logGasR
                    decoded["r_gas"] = gasR

                if (flags & 0x80) :  # get the miscellaneous flags
                    rawFlags = bytes [ i ]
                    i += 1

                    iaqQuality = rawFlags & 3

                    decoded["iaqQuality"] = iaqQuality


            else :
                # cmd value not recognized.
                print(cmd)

        elif (port == 2) :
            # see catena-message-port2-format.md
            # i is used as the index into the message. Start with the flag byte.
            # note that there's no discriminator.
            i = 0
            # fetch the bitmap.
            flags = bytes [ i ]
            i += 1

            if (flags & 0x1) :
                # set vRaw to a uint16, and increment pointer
                vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                # interpret uint16 as an int16 instead.
                if (vRaw & 0x8000):
                    vRaw += -0x10000
                # scale and save in decoded["
                decoded["vBat"] = vRaw / 4096.0

            if (flags & 0x2) :
                VDDRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                if (VDDRaw & 0x8000):
                    VDDRaw += -0x10000
                decoded["VDD"] = VDDRaw / 4096.0

            if (flags & 0x4) :
                iBoot = bytes [ i ]
                i += 1
                decoded["boot"] = iBoot

            if (flags & 0x8) :
                # we have temp, pressure, RH
                tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                if (tRaw & 0x8000):
                    tRaw = -0x10000 + tRaw
                i += 2
                pRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                hRaw = bytes [ i ]
                i += 1

                decoded["tempC"] = tRaw / 256
                decoded["error"] = "none"
                decoded["p"] = pRaw * 4 / 100.0
                decoded["rh"] = hRaw / 256 * 100
                decoded["tDewC"] = self.dewpoint ( decoded["tempC"] , decoded["rh"] )

            if (flags & 0x10) :
                # we have IR, White, UV -- units are C * W/m2,
                # where C is a calibration constant.
                irradiance = {}
                decoded["irradiance"] = irradiance
                lightRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                irradiance.IR = lightRaw
                lightRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                irradiance.White = lightRaw
                lightRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                irradiance.UV = lightRaw

            if (flags & 0x20) :
                vRawBus = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                if (vRawBus & 0x8000):
                    vRawBus += -0x10000
                decoded["vBus"] = vRawBus / 4096.0

        elif (port == 3) :
            # see catena-message-port3-format.md
            # i is used as the index into the message. Start with the flag byte.
            # note that there's no discriminator.
            i = 0
            # fetch the bitmap.
            flags = bytes [ i ]
            i += 1

            if (flags & 0x1) :
                # set vRaw to a uint16, and increment pointer
                vRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                # interpret uint16 as an int16 instead.
                if (vRaw & 0x8000):
                    vRaw += -0x10000
                # scale and save in decoded["
                decoded["vBat"] = vRaw / 4096.0

            if (flags & 0x2) :
                VDDRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                if (VDDRaw & 0x8000):
                    VDDRaw += -0x10000
                decoded["VDD"] = VDDRaw / 4096.0

            if (flags & 0x4) :
                iBoot = bytes [ i ]
                i += 1
                decoded["boot"] = iBoot

            if (flags & 0x8) :
                # we have temp, RH (as u2)
                tRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                if (tRaw & 0x8000):
                    tRaw = -0x10000 + tRaw
                i += 2
                rhRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2

                decoded["tempC"] = tRaw / 256
                decoded["error"] = "none"
                decoded["rh"] = rhRaw / 65535 * 100
                decoded["tDewC"] = self.dewpoint ( decoded["tempC"] , decoded["rh"] )

            if (flags & 0x10) :
                # we have IR, White, UV -- units are C * W/m2,
                # where C is a calibration constant.
                irradiance = {}
                decoded["irradiance"] = irradiance
                lightRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                irradiance.IR = lightRaw
                lightRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                irradiance.White = lightRaw
                lightRaw = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                irradiance.UV = lightRaw

            if (flags & 0x20) :
                vRawBus = (bytes [ i ] << 8) + bytes [ i + 1 ]
                i += 2
                if (vRawBus & 0x8000):
                    vRawBus += -0x10000
                decoded["vBus"] = vRawBus / 4096.0

        # at this point, decoded has the real values.
        return decoded


# Programme de test
if __name__ == "__main__":
    b64str = "FB1CRlgWdl9dOn1A"
    # {'vBat': 4.14208984375, 'boot': 88, 'tempC': 22.4609375, 'error': 'none', 'p': 976.52, 'rh': 22.65625, 'tDewC': 0.08705999718869349, 'lux': 32064}

    cdec = CatenaDecoder()
    print(cdec.parse(1, b64str))