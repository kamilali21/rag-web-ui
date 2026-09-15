// Added by ChatGPT: illustrative records from the wireframe, never presented as an actual UAF corpus.
export type ResearchDocument = {
  id: number;
  name: string;
  size: string;
  author: string;
  department: string;
  date: string;
  type: "Paper" | "Thesis" | "Report";
};

export const sampleDocuments: ResearchDocument[] = [
  { id: 1, name: "Deep Learning for Plant Disease Detection in Crop Images.pdf", size: "2.4 MB", author: "Ayesha Rahman", department: "Computer Science", date: "2024-03-10", type: "Paper" },
  { id: 2, name: "Soil Microbiome and Crop Yield Resilience.pdf", size: "1.1 MB", author: "Dr. James Wilson", department: "Plant Pathology", date: "2024-03-08", type: "Paper" },
  { id: 3, name: "Climate Change Impacts on Maize Productivity in South Asia.pdf", size: "856.3 KB", author: "Fatima Khan", department: "Agronomy", date: "2024-03-05", type: "Thesis" },
  { id: 4, name: "Nutritional Analysis of Alternative Protein Sources.pdf", size: "1.8 MB", author: "Dr. Emily Carter", department: "Food Science", date: "2024-03-01", type: "Report" },
  { id: 5, name: "Feed Additives and Livestock Growth Performance.pdf", size: "670.2 KB", author: "Muhammad Ali", department: "Animal Nutrition", date: "2024-02-27", type: "Paper" },
];

export function researchDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}
