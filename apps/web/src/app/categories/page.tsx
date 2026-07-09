import { CategoryManager } from "@/components/category-manager";
import { listCategories } from "@/lib/knowledge-api";

export default async function CategoriesPage() {
  const categories = await listCategories();

  return (
    <main className="page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Categories</p>
          <h1>分类管理</h1>
          <p className="page-description">
            主分类用于稳定导航。系统分类保持少量，自定义分类用于补充你的领域结构。
          </p>
        </div>
      </div>
      <CategoryManager categories={categories} />
    </main>
  );
}

