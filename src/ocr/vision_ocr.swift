import Foundation
import ImageIO
import Vision

func fail(_ message: String, _ code: Int32 = 1) -> Never {
    FileHandle.standardError.write(Data(message.utf8))
    exit(code)
}

guard CommandLine.arguments.count == 2 else { fail("Expected one image path.") }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
      let width = properties[kCGImagePropertyPixelWidth] as? Int,
      let height = properties[kCGImagePropertyPixelHeight] as? Int,
      width > 0, height > 0, width <= 12_000, height <= 12_000,
      width * height <= 24_000_000,
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fail("Image is invalid or exceeds the 24 megapixel OCR limit.")
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
let handler = VNImageRequestHandler(cgImage: image)
do {
    try handler.perform([request])
    let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    print(lines.joined(separator: "\n"), terminator: "")
} catch {
    fail("Apple Vision could not recognize text in this image.")
}
