using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading;
using iGameAPI.Contracts.LCD;
using iGameAPI.LCD.CSharp;

namespace IGamePet
{
    class Program
    {
        static LCD5A s_lcd5a;

        static void Main(string[] args)
        {
            Console.OutputEncoding = System.Text.Encoding.UTF8;

            string igameDir = @"C:\Program Files\iGameCenter";
            string igameApiDir = Path.Combine(igameDir, "iGameAPI");
            string n15Dir = Path.Combine(igameApiDir, "N15_25");
            string curPath = Environment.GetEnvironmentVariable("PATH") ?? "";
            Environment.SetEnvironmentVariable("PATH", igameDir + ";" + igameApiDir + ";" + n15Dir + ";" + curPath);

            AppDomain.CurrentDomain.AssemblyResolve += (s, ea) =>
            {
                string name = new AssemblyName(ea.Name).Name;
                string exeDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                string[] dirs = { exeDir, igameDir, igameApiDir, n15Dir,
                    Path.Combine(igameDir, "DB"), Path.Combine(igameDir, "ImageProcessor") };
                foreach (string d in dirs)
                {
                    string p = Path.Combine(d, name + ".dll");
                    if (File.Exists(p)) return Assembly.LoadFrom(p);
                }
                return null;
            };

            if (args.Length == 0) { PrintHelp(); return; }

            string cmd = args[0].ToLower();
            try
            {
                switch (cmd)
                {
                    case "detect": Detect(); break;
                    case "list": ListImages(); break;
                    case "info": ShowInfo(); break;
                    case "play": CmdPlay(args); break;
                    case "delete": CmdDelete(args); break;
                    case "pet": CmdPet(); break;
                    case "upload": CmdUpload(args); break;
                    default: PrintHelp(); break;
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("[ERROR] " + ex.Message);
                Console.Error.WriteLine(ex.StackTrace);
            }
            finally { CloseDevice(); }
        }

        // ── Device Connection (FIXED: use object from GetLCDGeneralCOM directly) ──

        static LCD5A Connect()
        {
            if (s_lcd5a != null) return s_lcd5a;

            Log("Scanning for LCD5A...");
            var list = LCD.GetLCDGeneralCOM((msg) => { /* quiet */ });
            if (list == null || list.Count == 0)
                throw new Exception("No iGame LCD device found.");

            for (int i = 0; i < list.Count; i++)
            {
                if (list[i].Version != LCD_IC_VERSION.LCD5A) continue;

                // KEY FIX: GetLCDGeneralCOM() already creates & opens the device.
                // Use the returned LCD5A directly. Do NOT create a new one.
                LCD5A dev = list[i] as LCD5A;
                if (dev == null)
                {
                    Log("WARNING: ILCD is not LCD5A type, creating wrapper...");
                    string port = GetCOMPort(list[i]);
                    dev = new LCD5A(port, (msg) => { });
                    dev.Start();
                }
                else
                {
                    Log("Using device from GetLCDGeneralCOM (already started)");
                }

                s_lcd5a = dev;
                try { s_lcd5a.SetLang(1); } catch { }
                return s_lcd5a;
            }

            throw new Exception("LCD5A not found in scan results.");
        }

        static string GetCOMPort(ILCD lcd)
        {
            string[] propNames = { "LCD5APortName", "ComPortName", "COMName", "PortName" };
            var t = lcd.GetType();
            foreach (string n in propNames)
            {
                var p = t.GetProperty(n);
                if (p != null)
                {
                    string v = p.GetValue(lcd, null) as string;
                    if (!string.IsNullOrEmpty(v)) return v;
                }
            }
            // Get from core's LCD5APortName property as last resort
            try
            {
                var f = t.GetField("LCD5ACore", BindingFlags.NonPublic | BindingFlags.Instance);
                if (f != null)
                {
                    var core = f.GetValue(lcd);
                    var pp = core.GetType().GetProperty("LCD5APortName");
                    if (pp != null)
                    {
                        string v = pp.GetValue(core, null) as string;
                        if (!string.IsNullOrEmpty(v)) return v;
                    }
                }
            }
            catch { }
            return "COM8";
        }

        static void CloseDevice()
        {
            if (s_lcd5a != null)
            {
                try { s_lcd5a.Close(); } catch { }
                s_lcd5a = null;
            }
        }

        // ── Commands ──

        static void Detect()
        {
            Log("=== iGame LCD5A Diagnostic ===");
            try
            {
                var list = LCD.GetLCDGeneralCOM((msg) => { });
                if (list != null && list.Count > 0)
                {
                    for (int i = 0; i < list.Count; i++)
                    {
                        Log(string.Format("  LCD#{0}: {1}, Type: {2}, GPUHandle: {3}",
                            i + 1, list[i].Version, list[i].GetType().Name,
                            list[i].GPUHandle != IntPtr.Zero ? "yes" : "no"));

                        // Check if it's an LCD5A with accessible SerialPort
                        var lcd5a = list[i] as LCD5A;
                        if (lcd5a != null)
                        {
                            try
                            {
                                var coreField = typeof(LCD5A).GetField("LCD5ACore",
                                    BindingFlags.NonPublic | BindingFlags.Instance);
                                if (coreField != null)
                                {
                                    var core = coreField.GetValue(lcd5a);
                                    var portP = core.GetType().GetProperty("LCD5APortName");
                                    if (portP != null)
                                        Log("    Port: " + portP.GetValue(core, null));
                                    var isOpenM = core.GetType().GetMethod("IsOpenCom");
                                    if (isOpenM != null)
                                        Log("    IsOpenCom: " + isOpenM.Invoke(core, null));
                                }
                            }
                            catch { }
                        }
                    }
                }
                else
                {
                    Log("  No devices found");
                }
            }
            catch (Exception ex) { Log("  Error: " + ex.Message); }
        }

        static void ShowInfo()
        {
            var l = Connect();
            Console.WriteLine("\n=== LCD5A Device Info ===");
            try { Console.WriteLine("  Screen size: {0}\"", l.GetLCDSize()); } catch { }
            try { Console.WriteLine("  Brightness: {0}", l.Brightness); } catch { }
            try
            {
                var setting = l.GetSetting();
                Console.WriteLine("  Setting:");
                var st = setting.GetType();
                foreach (var prop in st.GetProperties())
                {
                    try { Console.WriteLine("    {0} = {1}", prop.Name, prop.GetValue(setting, null)); }
                    catch { }
                }
            }
            catch (Exception ex) { Console.WriteLine("  Setting error: " + ex.Message); }
            try
            {
                var images = l.GetImages();
                Console.WriteLine("  Files stored: {0}", images != null ? images.Count : 0);
                if (images != null)
                    foreach (var img in images)
                        Console.WriteLine("    - {0} ({1} bytes)", img.FileName, img.FileSize);
            }
            catch (Exception ex) { Console.WriteLine("  GetImages error: " + ex.Message); }
        }

        static void ListImages()
        {
            var l = Connect();
            try
            {
                var images = l.GetImages();
                int count = (images != null) ? images.Count : 0;
                Console.WriteLine("\nStored files ({0}):", count);
                if (images != null)
                {
                    int idx = 0;
                    foreach (var img in images)
                        Console.WriteLine("  [{0}] {1}", idx++, img.FileName);
                }
            }
            catch (Exception ex) { Console.Error.WriteLine("List error: " + ex.Message); }
        }

        static void CmdPlay(string[] args)
        {
            if (args.Length < 2) { Console.WriteLine("Usage: iGamePet play <filename>"); return; }
            var l = Connect();
            string name = args[1];
            Log("Playing: " + name);
            Thread.Sleep(200);
            l.PlayMov(name);
            Log("OK - check the mini screen!");
        }

        static void CmdDelete(string[] args)
        {
            if (args.Length < 2) { Console.WriteLine("Usage: iGamePet delete <filename>"); return; }
            var l = Connect();
            l.DeleteMov(args[1]);
            Log("Deleted: " + args[1]);
        }

        static void CmdUpload(string[] args)
        {
            if (args.Length < 2) { Console.WriteLine("Usage: iGamePet upload <filePath> [name]"); return; }

            string filePath = Path.GetFullPath(args[1]);
            string name = args.Length > 2 ? args[2] : Path.GetFileNameWithoutExtension(filePath);

            if (!File.Exists(filePath))
            {
                Console.Error.WriteLine("[ERROR] File not found: " + filePath);
                return;
            }

            var l = Connect();
            long fileSize = new FileInfo(filePath).Length;
            Log(string.Format("Uploading: {0} ({1} KB) as '{2}'", Path.GetFileName(filePath), fileSize / 1024, name));

            try
            {
                var task = l.UploadImage(name, filePath);
                bool ok = task.GetAwaiter().GetResult();

                if (ok)
                {
                    Log("Upload OK! Setting as active and playing...");
                    try { l.SetStartIMG(name); } catch { }
                    l.PlayMov(name);
                    Log("Check the mini screen now!");
                }
                else
                {
                    Console.Error.WriteLine("[ERROR] Upload returned false");
                }
            }
            catch (AggregateException ae)
            {
                string msg = ae.InnerException != null ? ae.InnerException.Message : ae.Message;
                Console.Error.WriteLine("[ERROR] Upload failed: " + msg);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("[ERROR] Upload failed: " + ex.Message);
            }
        }

        static void CmdPet()
        {
            var l = Connect();
            string gifPath = Path.GetFullPath(Path.Combine(
                Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), "..", "output", "pet.gif"));

            if (File.Exists(gifPath))
            {
                Log("Uploading pet.gif...");
                try
                {
                    var task = l.UploadImage("mypet", gifPath);
                    if (task.GetAwaiter().GetResult())
                    {
                        l.PlayMov("mypet");
                        Console.WriteLine("\n  Desktop pet is live on screen!");
                        return;
                    }
                }
                catch (Exception ex) { Log("Upload failed: " + ex.Message); }
            }

            // Fallback
            Log("Trying IMG1.gif...");
            l.PlayMov("IMG1.gif");
            Console.WriteLine("\n  Check the mini screen!");
        }

        // ── Helpers ──

        static void PrintHelp()
        {
            Console.WriteLine(@"
iGamePet - LCD5A Mini Screen Controller
========================================
Commands:
  detect       Scan for connected devices
  info         Show device info
  list         List animations
  play <name>  Play an animation
  delete <name> Delete an animation
  upload <file> [name]  Upload GIF and play
  pet          One-click: upload & play pet.gif

Examples:
  iGamePet detect
  iGamePet list
  iGamePet upload C:\my.gif mypet
  iGamePet play mypet
");
        }

        static void Log(string msg) { Console.WriteLine("[iGamePet] " + msg); }
    }
}
