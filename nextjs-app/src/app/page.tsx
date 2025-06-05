"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AlertCircle, CheckCircle, Upload, Download, Shield } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import axios from "axios"

export default function Home() {
  // State untuk menyimpan file yang dipilih
  const [file, setFile] = useState<File | null>(null)
  const [username, setUsername] = useState("") // State untuk username
  const [keyword, setKeyword] = useState("") // State untuk kata kunci
  const [message, setMessage] = useState<{ type: "success" | "error" | "info" | null; text: string }>({
    type: null,
    text: "",
  })
  const [isLoading, setIsLoading] = useState(false) // State untuk status loading
  const [downloadUrl, setDownloadUrl] = useState<{ url: string; filename: string } | null>(null)
  const [activeTab, setActiveTab] = useState<"encrypt" | "decrypt" | "verify">("encrypt")

  const AESDescription = {
    encryption: {
      title: "Enkripsi File",
      description: "File Anda akan diamankan menggunakan algoritma AES. Kunci enkripsi akan dibuat otomatis dan disimpan di server, namun nama file kunci tersebut diamankan dengan enkripsi Vigenère berdasarkan username dan kata kunci yang Anda masukkan."
    },
    decryption: {
      title: "Dekripsi File",
      description: "Untuk membuka file yang telah dienkripsi, sistem akan menggunakan kunci yang sama seperti saat proses enkripsi. Nama file kunci hanya dapat ditemukan jika Anda memasukkan username dan kata kunci yang sama."
    },
    verification: {
      title: "Verifikasi File",
      description: "Sistem akan membandingkan hash file yang Anda upload dengan hash file asli yang disimpan saat proses enkripsi, untuk memastikan file tidak berubah atau rusak."
    },
  }

  // Fungsi untuk menangani perubahan file yang dipilih
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setMessage({ type: "info", text: `File dipilih: ${e.target.files[0].name}` })
    }
  }

  // Fungsi untuk mereset URL unduhan
  const handleDownloadReset = () => {
    if (downloadUrl) {
      window.URL.revokeObjectURL(downloadUrl.url)
      setDownloadUrl(null)
    }
  }

  // Membersihkan URL unduhan saat komponen di-unmount
  useEffect(() => {
    return () => {
      if (downloadUrl) {
        window.URL.revokeObjectURL(downloadUrl.url)
      }
    };
  }, [downloadUrl]);

  // Fungsi untuk menangani operasi enkripsi, dekripsi, atau verifikasi
  const handleOperation = async (operation: "encrypt" | "decrypt" | "verify") => {
    if (!username || !keyword) {
      setMessage({ type: "error", text: "Masukkan username dan kata kunci Anda" });
      return;
    }

    if (!file) {
      setMessage({ type: "error", text: "Pilih file terlebih dahulu" });
      return;
    }

    setIsLoading(true);
    setMessage({ type: "info", text: `Memproses file Anda...` });

    const formData = new FormData();
    formData.append("file", file);
    formData.append("username", username);
    formData.append("keyword", keyword);

    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/file/${operation}`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        responseType: "blob", // Mengatur tipe respons menjadi blob
      });

      if (response.status === 200) {
        if (operation !== "verify") {
          const blob = new Blob([response.data], { type: response.headers["content-type"] });
          const contentDisposition = response.headers["content-disposition"];
          let filename = "file_diproses";

          // Ekstrak nama file dari header Content-Disposition
          if (contentDisposition && contentDisposition.includes("filename=")) {
            const match = contentDisposition.match(/filename="(.+)"/);
            if (match && match[1]) {
              filename = match[1];
            }
          }

          const url = window.URL.createObjectURL(blob);
          setDownloadUrl({ url, filename });
        }

        const text = operation === "encrypt"
          ? "File berhasil dienkripsi"
          : operation === "decrypt"
            ? "File berhasil didekripsi"
            : "File berhasil diverifikasi";

        setMessage({ type: "success", text });
      } else {
        const data = await response.data;
        setMessage({ type: "error", text: data.detail || "Terjadi kesalahan" });
      }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        const contentType = error.response.headers["content-type"];
        if (contentType && contentType.includes("application/json")) {
          // Parsing respons error JSON dari Blob
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result as string);
              console.log(errorData); // Debugging
              setMessage({ type: "error", text: errorData.detail || "Terjadi kesalahan" });
            } catch {
              setMessage({ type: "error", text: "Gagal memproses respons error" });
            }
          };
          reader.readAsText(error.response.data); // Membaca Blob sebagai teks
        } else {
          setMessage({ type: "error", text: "Format error tidak dikenali dari server" });
        }
      } else {
        setMessage({ type: "error", text: "Gagal memproses file" });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
      {/* <NavigationBar /> */}
      <Card className="w-full max-w-4xl">
        <CardHeader>
          <CardTitle>Alat Enkripsi File</CardTitle>
          <CardDescription>
            Amankan file Anda dengan enkripsi, dekripsi, dan verifikasi
            <p>
              AES (Advanced Encryption Standard) menggunakan kunci yang sama untuk enkripsi dan dekripsi, karena itu kunci yang dihasilkan akan disimpan di server dengan enkripsi Vigenère dari username dan kata kunci Anda.
            </p>
          </CardDescription>
          <CardContent className="flex gap-4 p-0 py-4">

            {/* Bagian Username dan Kata Kunci */}
            <Card className="w-2/4">
              <CardHeader>
                <CardTitle>Vigenère Cipher</CardTitle>
                <CardDescription>Enkripsi detail pengguna menggunakan Vigenère cipher</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    type="text"
                    placeholder="Masukkan username Anda"
                    className="w-full"
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="keyword">Kata Kunci</Label>
                  <Input
                    id="keyword"
                    type="password"
                    placeholder="Masukkan kata kunci Anda"
                    className="w-full"
                    onChange={(e) => setKeyword(e.target.value)}
                  />
                </div>
                <div className="text-sm text-gray-500">
                  Username dan kata kunci digunakan untuk mengidentifikasi file dan menyimpannya dengan aman.
                </div>
              </CardContent>
            </Card>

            {/* Bagian Enkripsi */}
            <Card className="w-full">
              <CardHeader>
                <CardTitle>
                  {activeTab === "encrypt" && AESDescription.encryption.title}
                  {activeTab === "decrypt" && AESDescription.decryption.title}
                  {activeTab === "verify" && AESDescription.verification.title}
                </CardTitle>
                <CardDescription>
                  {activeTab === "encrypt" && AESDescription.encryption.description}
                  {activeTab === "decrypt" && AESDescription.decryption.description}
                  {activeTab === "verify" && AESDescription.verification.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs
                  defaultValue="encrypt"
                  className="w-full"
                  onValueChange={(val) => {
                    setActiveTab(val as "encrypt" | "decrypt" | "verify")
                    handleDownloadReset()
                  }}
                >
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="encrypt">Enkripsi</TabsTrigger>
                    <TabsTrigger value="verify">Verifikasi</TabsTrigger>
                    <TabsTrigger value="decrypt">Dekripsi</TabsTrigger>
                  </TabsList>

                  <TabsContent value="encrypt">
                    <div className="space-y-4 mt-4">
                      <div className="space-y-2">
                        <Label htmlFor="file-upload">Pilih File untuk Dienkripsi</Label>
                        <Input id="file-upload" type="file" onChange={handleFileChange} />
                      </div>

                      <Button onClick={() => handleOperation("encrypt")} className="w-full" disabled={isLoading}>
                        <Upload className="mr-2 h-4 w-4" />
                        {isLoading ? "Memproses..." : "Enkripsi File"}
                      </Button>
                    </div>
                  </TabsContent>

                  <TabsContent value="verify">
                    <div className="space-y-4 mt-4">
                      <div className="space-y-2">
                        <Label htmlFor="file-verify">Pilih File untuk Diverifikasi</Label>
                        <Input id="file-verify" type="file" onChange={handleFileChange} />
                      </div>

                      <Button onClick={() => handleOperation("verify")} className="w-full" disabled={isLoading}>
                        <Shield className="mr-2 h-4 w-4" />
                        {isLoading ? "Memverifikasi..." : "Verifikasi File"}
                      </Button>
                    </div>
                  </TabsContent>

                  <TabsContent value="decrypt">
                    <div className="space-y-4 mt-4">
                      <div className="space-y-2">
                        <Label htmlFor="file-decrypt">Pilih File Terenkripsi (.enc)</Label>
                        <Input id="file-decrypt" type="file" onChange={handleFileChange} />
                      </div>

                      <Button onClick={() => handleOperation("decrypt")} className="w-full" disabled={isLoading}>
                        <Download className="mr-2 h-4 w-4" />
                        {isLoading ? "Memproses..." : "Dekripsi File"}
                      </Button>
                    </div>
                  </TabsContent>
                </Tabs>

                {message.type && (
                  <Alert className="mt-4" variant={message.type === "error" ? "destructive" : "default"}>
                    {message.type === "success" ? (
                      <CheckCircle className="h-4 w-4 " />
                    ) : message.type === "error" ? (
                      <AlertCircle className="h-4 w-4" />
                    ) : (
                      <AlertCircle className="h-4 w-4" />
                    )}
                    <AlertTitle>
                      {message.type === "success" ? "Berhasil" : message.type === "error" ? "Kesalahan" : "Info"}
                    </AlertTitle>
                    <AlertDescription>{message.text}</AlertDescription>
                  </Alert>
                )}

                {downloadUrl && (
                  <div className="mt-4">
                    <Button asChild variant="outline" className="w-full">
                      <a href={downloadUrl.url} download={downloadUrl.filename}>
                        <Download className="mr-2 h-4 w-4" />
                        Unduh File yang Diproses
                      </a>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </CardContent>
        </CardHeader>
      </Card>
    </main>
  )
}