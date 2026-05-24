"""
stm32_sign_tool — графическая утилита для работы с криптомодулем STM32F103C8T6.

Реализует функции:
    * подключение к устройству по виртуальному COM-порту (USB CDC);
    * вычисление belt-hash файла или строки (на стороне ПК и на стороне устройства);
    * подписание хэша (bign-128, СТБ 34.101.45) с приватным ключом устройства;
    * проверка подписи bign-128;
    * генерация новой пары ключей и считывание публичного ключа;
    * шифрование/расшифрование произвольных данных в режиме belt-CBC.

Зависит от: pyserial (`pip install pyserial`).
"""
from __future__ import annotations

import os
import secrets
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from belt import pkcs7_pad, pkcs7_unpad
from belt_hash import belt_hash, belt_hash_file
from stm32_protocol import (
    BLOCK_LEN,
    DeviceError,
    HASH_LEN,
    KEY_LEN,
    PUBKEY_LEN,
    SIG_LEN,
    STM32Crypto,
    find_stm32_ports,
)

APP_TITLE = "Криптомодуль STM32 — СТБ 34.101.31/45"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x680")

        self.client: STM32Crypto | None = None

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self._refresh_ports()

    # ------------------------------------------------------------------- UI -
    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        ttk.Label(bar, text="Порт:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_cb = ttk.Combobox(bar, textvariable=self.port_var, width=18)
        self.port_cb.pack(side=tk.LEFT, padx=4)

        ttk.Button(bar, text="Обновить", command=self._refresh_ports).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Подключить", command=self._connect).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Отключить", command=self._disconnect).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Тест связи (PING)", command=self._ping).pack(side=tk.LEFT, padx=8)

    def _build_tabs(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.nb = nb
        self.tab_keys = ttk.Frame(nb); nb.add(self.tab_keys, text="Ключи")
        self.tab_sign = ttk.Frame(nb); nb.add(self.tab_sign, text="Подпись / проверка")
        self.tab_crypt = ttk.Frame(nb); nb.add(self.tab_crypt, text="Шифрование")
        self.tab_log = ttk.Frame(nb);  nb.add(self.tab_log, text="Журнал")

        self._build_tab_keys()
        self._build_tab_sign()
        self._build_tab_crypt()
        self._build_tab_log()

    def _build_statusbar(self) -> None:
        self.status = tk.StringVar(value="Не подключено.")
        ttk.Label(self, textvariable=self.status, anchor="w",
                  relief="sunken").pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------ Tab: keys -
    def _build_tab_keys(self) -> None:
        f = self.tab_keys
        ttk.Label(f, text="Публичный ключ устройства (64 байта, hex):").pack(anchor="w", padx=8, pady=(8, 0))
        self.pub_text = tk.Text(f, height=4, font=("Consolas", 10), wrap="word")
        self.pub_text.pack(fill=tk.X, padx=8, pady=4)

        bar = ttk.Frame(f); bar.pack(fill=tk.X, padx=8)
        ttk.Button(bar, text="Прочитать публичный ключ", command=self._get_pubkey).pack(side=tk.LEFT)
        ttk.Button(bar, text="Сгенерировать новую пару", command=self._gen_keypair).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Сохранить в файл", command=self._save_pubkey).pack(side=tk.LEFT, padx=8)

        ttk.Separator(f, orient="horizontal").pack(fill=tk.X, padx=8, pady=10)
        ttk.Label(f, text="Внимание: при генерации новой пары предыдущий приватный ключ\n"
                          "стирается из Flash микроконтроллера, и подписи, выпущенные\n"
                          "старым ключом, перестают проверяться имеющимся pubkey.",
                  foreground="#a00").pack(anchor="w", padx=8)

    def _get_pubkey(self) -> None:
        self._async(self._do_get_pubkey)

    def _do_get_pubkey(self) -> None:
        if not self._require_connected(): return
        pk = self.client.get_pubkey()
        self.pub_text.delete("1.0", tk.END)
        self.pub_text.insert("1.0", pk.hex().upper())
        self._log(f"GET_PUBKEY: {len(pk)} bytes\n  {pk.hex()}")

    def _gen_keypair(self) -> None:
        if not messagebox.askokcancel(
                "Подтверждение",
                "Сгенерировать новую пару ключей?\n\n"
                "Старая пара будет безвозвратно стёрта из Flash."):
            return
        self._async(self._do_gen_keypair)

    def _do_gen_keypair(self) -> None:
        if not self._require_connected(): return
        pk = self.client.gen_keypair()
        self.pub_text.delete("1.0", tk.END)
        self.pub_text.insert("1.0", pk.hex().upper())
        self._log(f"GEN_KEYPAIR: новый pubkey {pk.hex()}")

    def _save_pubkey(self) -> None:
        pk_hex = self.pub_text.get("1.0", tk.END).strip().replace("\n", "")
        if len(pk_hex) != PUBKEY_LEN * 2:
            messagebox.showerror("Ошибка", "Нет публичного ключа для сохранения")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pub",
                                            filetypes=[("Публичный ключ", "*.pub"),
                                                       ("All files", "*")])
        if not path: return
        Path(path).write_bytes(bytes.fromhex(pk_hex))
        self._log(f"Публичный ключ сохранён в {path}")

    # ------------------------------------------------------------ Tab: sign -
    def _build_tab_sign(self) -> None:
        f = self.tab_sign

        # источник данных
        src = ttk.LabelFrame(f, text="Данные для подписи / проверки")
        src.pack(fill=tk.X, padx=8, pady=6)
        self.sign_path = tk.StringVar()
        ttk.Entry(src, textvariable=self.sign_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
        ttk.Button(src, text="Файл…", command=self._pick_sign_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(src, text="belt-hash на ПК", command=self._compute_hash_local).pack(side=tk.LEFT, padx=4)
        ttk.Button(src, text="belt-hash на устройстве", command=self._compute_hash_device).pack(side=tk.LEFT, padx=4)

        ttk.Label(f, text="Хэш файла (32 байта, hex):").pack(anchor="w", padx=8)
        self.hash_text = tk.Text(f, height=2, font=("Consolas", 10), wrap="word")
        self.hash_text.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(f, text="Подпись (48 байт, hex):").pack(anchor="w", padx=8)
        self.sig_text = tk.Text(f, height=3, font=("Consolas", 10), wrap="word")
        self.sig_text.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(f, text="Публичный ключ для проверки (64 байта, hex; пусто = взять у устройства):").pack(anchor="w", padx=8)
        self.verify_pk = tk.Text(f, height=4, font=("Consolas", 10), wrap="word")
        self.verify_pk.pack(fill=tk.X, padx=8, pady=2)

        bar = ttk.Frame(f); bar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(bar, text="Подписать", command=self._sign).pack(side=tk.LEFT)
        ttk.Button(bar, text="Проверить", command=self._verify).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Сохранить подпись", command=self._save_sig).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Загрузить подпись", command=self._load_sig).pack(side=tk.LEFT, padx=8)

    def _pick_sign_file(self) -> None:
        p = filedialog.askopenfilename()
        if p:
            self.sign_path.set(p)

    def _compute_hash_local(self) -> None:
        p = self.sign_path.get().strip()
        if not p or not os.path.isfile(p):
            messagebox.showerror("Ошибка", "Выберите файл")
            return
        h = belt_hash_file(p)
        self.hash_text.delete("1.0", tk.END)
        self.hash_text.insert("1.0", h.hex().upper())
        self._log(f"belt-hash (ПК) от {p}: {h.hex()}")

    def _compute_hash_device(self) -> None:
        self._async(self._do_compute_hash_device)

    def _do_compute_hash_device(self) -> None:
        if not self._require_connected(): return
        p = self.sign_path.get().strip()
        if not p or not os.path.isfile(p):
            messagebox.showerror("Ошибка", "Выберите файл")
            return
        data = Path(p).read_bytes()
        if len(data) > 1024:
            messagebox.showwarning("Внимание",
                                   "Файл будет хэшироваться на устройстве — это медленнее, "
                                   "а размер ограничен буфером (1 КБ).")
            data = data[:1024]
        h = self.client.hash(data)
        self.hash_text.delete("1.0", tk.END)
        self.hash_text.insert("1.0", h.hex().upper())
        self._log(f"belt-hash (STM32) от {p}: {h.hex()}")

    def _sign(self) -> None:
        self._async(self._do_sign)

    def _do_sign(self) -> None:
        if not self._require_connected(): return
        h_hex = self.hash_text.get("1.0", tk.END).strip().replace("\n", "")
        if len(h_hex) != HASH_LEN * 2:
            messagebox.showerror("Ошибка", f"Хэш должен быть {HASH_LEN} байт ({HASH_LEN*2} hex)")
            return
        sig = self.client.sign(bytes.fromhex(h_hex))
        self.sig_text.delete("1.0", tk.END)
        self.sig_text.insert("1.0", sig.hex().upper())
        self._log(f"SIGN ok: {sig.hex()}")

    def _verify(self) -> None:
        self._async(self._do_verify)

    def _do_verify(self) -> None:
        if not self._require_connected(): return
        try:
            h = bytes.fromhex(self.hash_text.get("1.0", tk.END).strip().replace("\n", ""))
            s = bytes.fromhex(self.sig_text.get("1.0", tk.END).strip().replace("\n", ""))
            pk_hex = self.verify_pk.get("1.0", tk.END).strip().replace("\n", "")
            if not pk_hex:
                pk = self.client.get_pubkey()
            else:
                pk = bytes.fromhex(pk_hex)
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Не hex: {e}")
            return
        ok = self.client.verify(h, s, pk)
        self._log(f"VERIFY: {'OK' if ok else 'BAD SIGNATURE'}")
        messagebox.showinfo("Результат", "Подпись действительна" if ok else "Подпись недействительна")

    def _save_sig(self) -> None:
        sig_hex = self.sig_text.get("1.0", tk.END).strip().replace("\n", "")
        if len(sig_hex) != SIG_LEN * 2:
            messagebox.showerror("Ошибка", "Нет корректной подписи")
            return
        path = filedialog.asksaveasfilename(defaultextension=".sig",
                                            filetypes=[("Signature", "*.sig"), ("All files", "*")])
        if not path: return
        Path(path).write_bytes(bytes.fromhex(sig_hex))
        self._log(f"Подпись сохранена в {path}")

    def _load_sig(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("Signature", "*.sig"), ("All files", "*")])
        if not p: return
        data = Path(p).read_bytes()
        if len(data) != SIG_LEN:
            messagebox.showerror("Ошибка", f"Подпись должна быть ровно {SIG_LEN} байт")
            return
        self.sig_text.delete("1.0", tk.END)
        self.sig_text.insert("1.0", data.hex().upper())

    # ----------------------------------------------------------- Tab: crypt -
    def _build_tab_crypt(self) -> None:
        f = self.tab_crypt

        src = ttk.LabelFrame(f, text="Входной файл")
        src.pack(fill=tk.X, padx=8, pady=6)
        self.crypt_path = tk.StringVar()
        ttk.Entry(src, textvariable=self.crypt_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
        ttk.Button(src, text="Файл…", command=lambda: self.crypt_path.set(filedialog.askopenfilename() or self.crypt_path.get())).pack(side=tk.LEFT, padx=4)

        keys = ttk.LabelFrame(f, text="Ключ и IV (hex)")
        keys.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(keys, text="Ключ (32 байта):").grid(row=0, column=0, sticky="w", padx=4)
        self.crypt_key = tk.StringVar()
        ttk.Entry(keys, textvariable=self.crypt_key, width=80).grid(row=0, column=1, sticky="we", padx=4)
        ttk.Button(keys, text="Случайно", command=self._gen_key).grid(row=0, column=2, padx=2)
        ttk.Label(keys, text="IV (16 байт):").grid(row=1, column=0, sticky="w", padx=4)
        self.crypt_iv = tk.StringVar()
        ttk.Entry(keys, textvariable=self.crypt_iv, width=80).grid(row=1, column=1, sticky="we", padx=4)
        ttk.Button(keys, text="Случайно", command=self._gen_iv).grid(row=1, column=2, padx=2)
        keys.columnconfigure(1, weight=1)

        bar = ttk.Frame(f); bar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(bar, text="Зашифровать на STM32", command=lambda: self._async(self._do_encrypt)).pack(side=tk.LEFT)
        ttk.Button(bar, text="Расшифровать на STM32", command=lambda: self._async(self._do_decrypt)).pack(side=tk.LEFT, padx=8)

        ttk.Label(f, text="Журнал операций:").pack(anchor="w", padx=8)
        self.crypt_info = tk.Text(f, height=10, font=("Consolas", 10), wrap="word")
        self.crypt_info.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    def _gen_key(self) -> None:
        self.crypt_key.set(secrets.token_bytes(KEY_LEN).hex())

    def _gen_iv(self) -> None:
        self.crypt_iv.set(secrets.token_bytes(BLOCK_LEN).hex())

    def _do_encrypt(self) -> None:
        self._crypt_op(encrypt=True)

    def _do_decrypt(self) -> None:
        self._crypt_op(encrypt=False)

    def _crypt_op(self, encrypt: bool) -> None:
        if not self._require_connected(): return
        try:
            key = bytes.fromhex(self.crypt_key.get().strip())
            iv  = bytes.fromhex(self.crypt_iv.get().strip())
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ключ/IV не hex: {e}")
            return
        if len(key) != KEY_LEN or len(iv) != BLOCK_LEN:
            messagebox.showerror("Ошибка", "Длина ключа должна быть 32 байта, IV — 16 байт")
            return
        src_path = self.crypt_path.get().strip()
        if not src_path or not os.path.isfile(src_path):
            messagebox.showerror("Ошибка", "Выберите входной файл")
            return
        data = Path(src_path).read_bytes()
        orig_len = len(data)
        if encrypt:
            # PKCS#7-padding: всегда добавляет 1..16 байт со значением = числу байт
            # паддинга. При расшифровке будет однозначно снят и восстановлен
            # исходный файл байт-в-байт (СТБ 34.101.31, без потерь длины).
            padded = pkcs7_pad(data, BLOCK_LEN)
            out = self.client.encrypt(iv, key, padded)
            sent_len = len(padded)
            recv_len = len(out)
            ext = ".belt"
        else:
            if len(data) == 0 or len(data) % BLOCK_LEN != 0:
                messagebox.showerror("Ошибка", "Зашифрованный файл должен быть ненулевой длины и кратен 16 байтам")
                return
            decrypted = self.client.decrypt(iv, key, data)
            sent_len = len(data)
            try:
                out = pkcs7_unpad(decrypted, BLOCK_LEN)
            except ValueError:
                messagebox.showerror("Ошибка",
                                     "Неверный PKCS#7 padding после расшифровки.\n"
                                     "Проверьте ключ и IV.")
                return
            recv_len = len(out)
            ext = ".plain"

        dst = filedialog.asksaveasfilename(defaultextension=ext,
                                           initialfile=os.path.basename(src_path) + ext)
        if not dst: return
        Path(dst).write_bytes(out)
        self.crypt_info.insert(tk.END, f"{'ENCRYPT' if encrypt else 'DECRYPT'} {src_path} → {dst}\n"
                                       f"   key={key.hex()}\n   iv={iv.hex()}\n"
                                       f"   исходный файл: {orig_len} байт\n"
                                       f"   передано на STM32: {sent_len} байт (с PKCS#7)\n"
                                       f"   результат: {recv_len} байт\n\n")

    # ------------------------------------------------------------- Tab: log -
    def _build_tab_log(self) -> None:
        self.log_text = tk.Text(self.tab_log, font=("Consolas", 9), wrap="word")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _log(self, msg: str) -> None:
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    # ---------------------------------------------------- Connection helpers
    def _refresh_ports(self) -> None:
        ports = find_stm32_ports()
        all_ports = ports + [p.device for p in __import__("serial.tools.list_ports", fromlist=["comports"]).comports()
                             if p.device not in ports]
        self.port_cb["values"] = all_ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])
        self._log(f"Найдены порты: {', '.join(all_ports) if all_ports else '(нет)'}")

    def _connect(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("Ошибка", "Выберите порт")
            return
        try:
            self.client = STM32Crypto(port)
            self.client.connect()
            self.status.set(f"Подключено к {port}.")
            self._log(f"Подключено к {port}")
        except Exception as e:
            self.client = None
            self.status.set("Не подключено.")
            messagebox.showerror("Ошибка подключения", str(e))

    def _disconnect(self) -> None:
        if self.client:
            self.client.disconnect()
            self.client = None
        self.status.set("Не подключено.")
        self._log("Отключено")

    def _ping(self) -> None:
        self._async(self._do_ping)

    def _do_ping(self) -> None:
        if not self._require_connected(): return
        resp = self.client.ping()
        msg = f"PING: {resp!r}"
        self._log(msg)
        self.status.set(msg)

    def _require_connected(self) -> bool:
        if not self.client or not self.client.connected:
            messagebox.showerror("Не подключено", "Сначала выполните «Подключить»")
            return False
        return True

    # ----------------------------------------------------- async выполнение
    def _async(self, fn) -> None:
        def runner():
            try:
                fn()
            except DeviceError as e:
                self._log(f"DeviceError: {e}")
                messagebox.showerror("Ошибка устройства", str(e))
            except Exception as e:
                self._log(f"Exception: {e}")
                messagebox.showerror("Ошибка", str(e))
        threading.Thread(target=runner, daemon=True).start()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
