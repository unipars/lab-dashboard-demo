import React, { useState, useMemo } from 'react';
import * as XLSX from 'xlsx';
import { 
  FileUp, 
  FileText, 
  LayoutDashboard, 
  CheckCircle, 
  AlertCircle, 
  ArrowDownCircle, 
  Download,
  Activity,
  User,
  Calendar
} from 'lucide-react';
import { ReportData, LabTest } from './types';
import BulletChart from './components/BulletChart';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { motion } from 'framer-motion';

const App: React.FC = () => {
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [officialMode, setOfficialMode] = useState(false);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const bstr = evt.target?.result;
      const wb = XLSX.read(bstr, { type: 'binary' });
      const wsname = wb.SheetNames[0];
      const ws = wb.Sheets[wsname];
      const data = XLSX.utils.sheet_to_json(ws) as any[];

      if (data.length > 0) {
        const tests: LabTest[] = data.map((row) => ({
          test_name: row.test_name,
          value: parseFloat(row.value),
          unit: row.unit,
          ref_low: parseFloat(row.ref_low),
          ref_high: parseFloat(row.ref_high),
          category: row.category,
        }));

        setReportData({
          patient_name: data[0].patient_name || 'Unknown Patient',
          report_date: data[0].report_date || new Date().toISOString().split('T')[0],
          tests,
        });
      }
    };
    reader.readAsBinaryString(file);
  };

  const getStatus = (test: LabTest) => {
    if (test.value < test.ref_low) return 'Low';
    if (test.value > test.ref_high) return 'High';
    return 'Normal';
  };

  const stats = useMemo(() => {
    if (!reportData) return null;
    const normal = reportData.tests.filter(t => getStatus(t) === 'Normal');
    const high = reportData.tests.filter(t => getStatus(t) === 'High');
    const low = reportData.tests.filter(t => getStatus(t) === 'Low');
    return { normal, high, low };
  }, [reportData]);

  const categories = useMemo(() => {
    if (!reportData) return [];
    return Array.from(new Set(reportData.tests.map(t => t.category)));
  }, [reportData]);

  const generatePDF = () => {
    if (!reportData) return;
    const doc = new jsPDF();
    
    // Header
    doc.setFontSize(20);
    doc.setTextColor(40, 40, 40);
    doc.text('Mashhad Pathobiology Lab', 14, 22);
    
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text(`Patient: ${reportData.patient_name}`, 14, 32);
    doc.text(`Date: ${reportData.report_date}`, 14, 38);
    
    let currentY = 45;

    categories.forEach((cat) => {
      doc.setFontSize(14);
      doc.setTextColor(0, 0, 0);
      doc.text(cat, 14, currentY);
      currentY += 5;

      const catTests = reportData.tests.filter(t => t.category === cat);
      const tableData = catTests.map(t => [
        t.test_name,
        t.value.toString(),
        t.unit,
        `${t.ref_low} - ${t.ref_high}`
      ]);

      autoTable(doc, {
        startY: currentY,
        head: [['Test', 'Result', 'Unit', 'Reference Range']],
        body: tableData,
        theme: 'striped',
        headStyles: { fillColor: [200, 200, 200], textColor: [0, 0, 0] },
        margin: { left: 14, right: 14 },
      });

      // @ts-ignore
      currentY = (doc as any).lastAutoTable.finalY + 15;
      
      if (currentY > 250) {
        doc.addPage();
        currentY = 20;
      }
    });

    doc.save(`Report_${reportData.patient_name}.pdf`);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="text-blue-600" size={28} />
            <h1 className="text-xl font-bold tracking-tight">Mashhad Pathobiology Lab</h1>
          </div>
          <div className="flex items-center gap-4">
            {reportData && (
              <div className="flex items-center bg-slate-100 rounded-lg p-1">
                <button 
                  onClick={() => setOfficialMode(false)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${!officialMode ? 'bg-white shadow-sm text-blue-600' : 'text-slate-600'}`}
                >
                  <LayoutDashboard className="inline-block mr-1.5" size={16} />
                  Dashboard
                </button>
                <button 
                  onClick={() => setOfficialMode(true)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${officialMode ? 'bg-white shadow-sm text-blue-600' : 'text-slate-600'}`}
                >
                  <FileText className="inline-block mr-1.5" size={16} />
                  Official Report
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {!reportData ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <div className="w-20 h-20 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mb-6">
              <FileUp size={40} />
            </div>
            <h2 className="text-2xl font-bold mb-2">Welcome to Lab Dashboard</h2>
            <p className="text-slate-500 mb-8 max-w-md">
              Upload your Excel file containing lab results to visualize clinical ranges and generate reports.
            </p>
            <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-semibold transition-colors shadow-lg shadow-blue-200 mb-4">
              Upload Excel File
              <input type="file" className="hidden" accept=".xlsx" onChange={handleFileUpload} />
            </label>
            <button 
              onClick={() => {
                setReportData({
                  patient_name: "Ali Rezaei",
                  report_date: "2024-06-01",
                  tests: [
                    { test_name: "Glucose (Fasting)", value: 105, unit: "mg/dL", ref_low: 70, ref_high: 99, category: "Biochemistry" },
                    { test_name: "Cholesterol", value: 185, unit: "mg/dL", ref_low: 120, ref_high: 200, category: "Lipid Profile" },
                    { test_name: "Triglycerides", value: 210, unit: "mg/dL", ref_low: 50, ref_high: 150, category: "Lipid Profile" },
                    { test_name: "Hemoglobin", value: 11.2, unit: "g/dL", ref_low: 13.5, ref_high: 17.5, category: "Hematology" },
                    { test_name: "WBC Count", value: 6.8, unit: "x10^3/uL", ref_low: 4.5, ref_high: 11.0, category: "Hematology" },
                    { test_name: "TSH", value: 2.5, unit: "uIU/mL", ref_low: 0.4, ref_high: 4.2, category: "Thyroid Profile" },
                  ]
                });
              }}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium underline underline-offset-4"
            >
              Or load sample data
            </button>
            <p className="mt-4 text-xs text-slate-400">Supported format: .xlsx</p>
          </div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            {/* Patient Info Bar */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap gap-8 items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center">
                  <User size={20} />
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase font-semibold">Patient Name</div>
                  <div className="font-bold text-slate-800">{reportData.patient_name}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center">
                  <Calendar size={20} />
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase font-semibold">Report Date</div>
                  <div className="font-bold text-slate-800">{reportData.report_date}</div>
                </div>
              </div>
              <div className="ml-auto">
                <button 
                  onClick={generatePDF}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-900 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-md"
                >
                  <Download size={18} />
                  Download PDF
                </button>
              </div>
            </div>

            {!officialMode && stats ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-bold text-slate-500 flex items-center gap-2">
                        <CheckCircle className="text-emerald-500" size={18} />
                        Normal
                      </h3>
                      <span className="text-3xl font-black text-emerald-500">{stats.normal.length}</span>
                    </div>
                    <div className="text-xs text-slate-400 line-clamp-2">
                      {stats.normal.map(t => t.test_name).join(', ')}
                    </div>
                  </div>
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm border-l-4 border-l-red-500">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-bold text-slate-500 flex items-center gap-2">
                        <AlertCircle className="text-red-500" size={18} />
                        High
                      </h3>
                      <span className="text-3xl font-black text-red-500">{stats.high.length}</span>
                    </div>
                    <div className="text-xs text-slate-400 line-clamp-2">
                      {stats.high.map(t => t.test_name).join(', ')}
                    </div>
                  </div>
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm border-l-4 border-l-orange-500">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-bold text-slate-500 flex items-center gap-2">
                        <ArrowDownCircle className="text-orange-500" size={18} />
                        Low
                      </h3>
                      <span className="text-3xl font-black text-orange-500">{stats.low.length}</span>
                    </div>
                    <div className="text-xs text-slate-400 line-clamp-2">
                      {stats.low.map(t => t.test_name).join(', ')}
                    </div>
                  </div>
                </div>

                <div className="space-y-12">
                  {categories.map((cat) => (
                    <section key={cat}>
                      <div className="flex items-center gap-3 mb-6">
                        <h2 className="text-2xl font-bold text-slate-800">🧪 {cat}</h2>
                        <div className="h-px flex-1 bg-slate-200"></div>
                      </div>
                      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
                          <table className="w-full text-left border-collapse">
                            <thead>
                              <tr className="bg-slate-50 text-slate-500 text-xs font-bold uppercase tracking-wider">
                                <th className="px-6 py-4">Test</th>
                                <th className="px-6 py-4">Result</th>
                                <th className="px-6 py-4">Unit</th>
                                <th className="px-6 py-4">Ref Range</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {reportData.tests
                                .filter(t => t.category === cat)
                                .map((test, idx) => {
                                  const status = getStatus(test);
                                  return (
                                    <tr 
                                      key={idx} 
                                      className={`${
                                        status === 'High' ? 'bg-red-50/50' : 
                                        status === 'Low' ? 'bg-orange-50/50' : ''
                                      } hover:bg-slate-50 transition-colors`}
                                    >
                                      <td className="px-6 py-4 font-medium">{test.test_name}</td>
                                      <td className="px-6 py-4">
                                        <div className="flex items-center gap-1.5">
                                          {status === 'High' && <span className="text-red-500">🔺</span>}
                                          {status === 'Low' && <span className="text-orange-500">🔻</span>}
                                          <span className={`font-bold ${
                                            status === 'High' ? 'text-red-600' : 
                                            status === 'Low' ? 'text-orange-600' : 'text-slate-700'
                                          }`}>
                                            {test.value}
                                          </span>
                                        </div>
                                      </td>
                                      <td className="px-6 py-4 text-slate-500 text-sm">{test.unit}</td>
                                      <td className="px-6 py-4 text-slate-500 text-sm">
                                        {test.ref_low} - {test.ref_high}
                                      </td>
                                    </tr>
                                  );
                                })}
                            </tbody>
                          </table>
                        </div>
                        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-2">
                           {reportData.tests
                            .filter(t => t.category === cat)
                            .map((test, idx) => (
                              <BulletChart 
                                key={idx}
                                val={test.value}
                                refLow={test.ref_low}
                                refHigh={test.ref_high}
                                unit={test.unit}
                                testName={test.test_name}
                                status={getStatus(test)}
                              />
                            ))}
                        </div>
                      </div>
                    </section>
                  ))}
                </div>
              </>
            ) : (
              <div className="max-w-4xl mx-auto bg-white p-12 rounded shadow-lg border border-slate-100">
                <div className="border-b-2 border-slate-800 pb-8 mb-8 text-center">
                  <h1 className="text-3xl font-black uppercase tracking-widest text-slate-900">Mashhad Pathobiology Lab</h1>
                  <p className="text-slate-500 mt-2">Accredited Clinical Laboratory & Diagnostic Center</p>
                </div>
                
                <div className="grid grid-cols-2 gap-8 mb-12 text-sm">
                  <div>
                    <div className="flex justify-between border-b border-slate-100 py-1">
                      <span className="text-slate-500 font-medium">Patient Name:</span>
                      <span className="font-bold">{reportData.patient_name}</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-100 py-1">
                      <span className="text-slate-500 font-medium">Patient ID:</span>
                      <span className="font-bold">#2024-8842</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between border-b border-slate-100 py-1">
                      <span className="text-slate-500 font-medium">Report Date:</span>
                      <span className="font-bold">{reportData.report_date}</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-100 py-1">
                      <span className="text-slate-500 font-medium">Sample Status:</span>
                      <span className="font-bold text-green-600">Processed</span>
                    </div>
                  </div>
                </div>

                {categories.map((cat) => (
                  <div key={cat} className="mb-12">
                    <h2 className="text-xl font-bold mb-4 pb-2 border-b border-slate-200">{cat}</h2>
                    <table className="w-full mb-6">
                      <thead>
                        <tr className="bg-slate-50 text-xs font-bold uppercase">
                          <th className="px-4 py-3 text-left">Test</th>
                          <th className="px-4 py-3 text-left">Result</th>
                          <th className="px-4 py-3 text-left">Unit</th>
                          <th className="px-4 py-3 text-left">Reference Range</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.tests
                          .filter(t => t.category === cat)
                          .map((test, idx) => {
                            const status = getStatus(test);
                            return (
                              <tr key={idx} className="border-b border-slate-100 text-sm">
                                <td className="px-4 py-3 font-medium">{test.test_name}</td>
                                <td className="px-4 py-3 font-bold">
                                  {test.value}
                                  {status !== 'Normal' && (
                                    <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded ${
                                      status === 'High' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                                    }`}>
                                      {status.toUpperCase()}
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-3 text-slate-500">{test.unit}</td>
                                <td className="px-4 py-3 text-slate-500">{test.ref_low} - {test.ref_high}</td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                    
                    <div className="space-y-1">
                      {reportData.tests
                        .filter(t => t.category === cat)
                        .map((test, idx) => (
                          <BulletChart 
                            key={idx}
                            val={test.value}
                            refLow={test.ref_low}
                            refHigh={test.ref_high}
                            unit={test.unit}
                            testName={test.test_name}
                            status={getStatus(test)}
                            isPdfMode
                          />
                        ))}
                    </div>
                  </div>
                ))}

                <div className="mt-20 flex justify-between items-end border-t border-slate-200 pt-8">
                  <div className="text-[10px] text-slate-400 max-w-xs">
                    This is a computer-generated report and does not require a physical signature. 
                    Please consult with your physician for clinical interpretation of these results.
                  </div>
                  <div className="text-right">
                    <div className="w-32 h-16 border border-slate-200 rounded flex items-center justify-center text-[10px] text-slate-300 mb-2">
                      Laboratory Seal
                    </div>
                    <div className="font-bold text-sm">Lab Director</div>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </main>

      {/* Floating Upload for when data exists */}
      {reportData && (
        <div className="fixed bottom-6 right-6">
          <label className="cursor-pointer bg-white border border-slate-200 text-slate-600 hover:text-blue-600 w-12 h-12 rounded-full flex items-center justify-center transition-all shadow-lg hover:shadow-xl group">
            <FileUp size={24} />
            <span className="absolute right-14 bg-white border border-slate-200 px-3 py-1.5 rounded-lg text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              Upload New File
            </span>
            <input type="file" className="hidden" accept=".xlsx" onChange={handleFileUpload} />
          </label>
        </div>
      )}
    </div>
  );
};

export default App;
